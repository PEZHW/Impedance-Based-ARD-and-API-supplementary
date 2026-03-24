"""
PINN-VSG: Physics-Informed Neural Network for VSG Impedance Modeling
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import os
import random


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class PINN_VSG(nn.Module):
    """
    Physics-Informed Neural Network for VSG Impedance

    Architecture:
    - Branch1 (Polynomial characteristic): [Ud, Uq, Id, Iq] → polynomial features
    - Branch2 (Generic Feature Extraction): [f, kpv, kiv, kpi] → frequency+control features
        → multi-head outputs:
          * Head1: Filter features
          * Head2: Control Loop features
          * Head3: Phase Rectification features
    - Fusion layer (feature fusion)
    - Output layer (Mag & Phase Calculation): 8 outputs
    """
    
    def __init__(self, config):
        super(PINN_VSG, self).__init__()
        
        self.poly_neurons = config.get('polynomial_neurons', 20)
        self.freq_neurons = config.get('frequency_neurons', 32)
        self.filter_neurons = config.get('filter_neurons', 4)
        self.control_neurons = config.get('control_neurons', 8)
        self.phase_neurons = config.get('phase_neurons', 4)
        self.fusion_neurons = config.get('fusion_neurons', 16)
        
        self.input_mean = None
        self.input_std = None
        self.output_mean = None
        self.output_std = None
        
        activation_type = config.get('activation', 'tanh')
        self.activation = self._get_activation(activation_type)
        
        # Branch 1: Operating point → polynomial features  [Ud, Uq, Id, Iq]
        self.branch1_layer1 = nn.Linear(4, self.poly_neurons)

        # Branch 2: Generic Feature Extraction  [f, kpv, kiv, kpi]
        self.branch2_layer1 = nn.Sequential(
            nn.Linear(4, self.freq_neurons),
            self.activation
        )
        
        # Multi-head outputs
        self.head_filter = nn.Sequential(
            nn.Linear(self.freq_neurons, self.filter_neurons),
            self.activation
        )
        self.head_control = nn.Sequential(
            nn.Linear(self.freq_neurons, self.control_neurons),
            self.activation
        )
        self.head_phase = nn.Sequential(
            nn.Linear(self.freq_neurons, self.phase_neurons),
            self.activation
        )
        
        # Fusion layer
        concat_size = self.poly_neurons + self.filter_neurons + self.control_neurons + self.phase_neurons
        self.fusion_layer = nn.Sequential(
            nn.Linear(concat_size, self.fusion_neurons),
            self.activation
        )
        
        # Output layer
        self.output_layer = nn.Linear(self.fusion_neurons, 8)
        
        self._initialize_weights()
    
    def _get_activation(self, activation_type):
        activation_map = {
            'sigmoid': nn.Sigmoid(),
            'relu': nn.ReLU(),
            'tanh': nn.Tanh(),
            'leaky_relu': nn.LeakyReLU(),
            'linear': nn.Identity()
        }
        return activation_map.get(activation_type.lower(), nn.Tanh())
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def set_normalization_params(self, input_data, output_data):
        self.input_mean = torch.tensor(np.mean(input_data, axis=0, dtype=np.float32))
        self.input_std = torch.tensor(np.std(input_data, axis=0, dtype=np.float32))
        self.output_mean = torch.tensor(np.mean(output_data, axis=0, dtype=np.float32))
        self.output_std = torch.tensor(np.std(output_data, axis=0, dtype=np.float32))
    
    def normalize_input(self, x):
        if self.input_mean is not None:
            device = x.device
            return (x - self.input_mean.to(device)) / (self.input_std.to(device) + 1e-8)
        return x
    
    def normalize_output(self, y):
        if self.output_mean is not None:
            device = y.device
            return (y - self.output_mean.to(device)) / (self.output_std.to(device) + 1e-8)
        return y
    
    def denormalize_output(self, y_normalized):
        if self.output_mean is not None:
            device = y_normalized.device
            return y_normalized * (self.output_std.to(device) + 1e-8) + self.output_mean.to(device)
        return y_normalized
    
    def forward(self, x):
        x = self.normalize_input(x)

        # Branch 1: [Ud, Uq, Id, Iq]  col 0-3
        operating_points = x[:, :4]
        # Branch 2: [f, kpv, kiv, kpi]  col 4-7
        freq_ctrl = x[:, 4:8]

        poly_features    = self.branch1_layer1(operating_points)
        freq_features    = self.branch2_layer1(freq_ctrl)

        filter_features  = self.head_filter(freq_features)
        control_features = self.head_control(freq_features)
        phase_features   = self.head_phase(freq_features)

        all_features  = torch.cat([poly_features, filter_features, control_features, phase_features], dim=1)
        fused_features = self.fusion_layer(all_features)
        impedance      = self.output_layer(fused_features)

        return impedance
    
    def get_architecture_info(self):
        return {
            'model_type': 'PINN_VSG',
            'total_params': sum(p.numel() for p in self.parameters()),
            'architecture': (
                f"Branch1 (Polynomial): 4→{self.poly_neurons} | "
                f"Branch2 (GenericFeat): 4→{self.freq_neurons} → "
                f"[Filter:{self.filter_neurons}, CtrlLoop:{self.control_neurons}, PhaseRect:{self.phase_neurons}] | "
                f"Fusion: {self.poly_neurons + self.filter_neurons + self.control_neurons + self.phase_neurons}"
                f"→{self.fusion_neurons}→8"
            )
        }


def load_and_split_by_condition(csv_file_path, train_ratio=0.75, val_ratio=0.15, random_seed=42):
    """按工况划分数据集"""
    print("\n" + "="*60)
    print("数据加载与按工况划分")
    print("="*60)
    
    data = pd.read_csv(csv_file_path, header=0)
    print(f"数据文件: {csv_file_path}")
    print(f"数据形状: {data.shape}")
    
    data_array = np.array(data, dtype=np.float32)
    # CSV列顺序: Ud Uq Id Iq kpv kiv kpi f | GM_Zdd PM_Zdd ... (共16列)
    input_data  = data_array[:, :8]   # [Ud, Uq, Id, Iq, kpv, kiv, kpi, f]
    output_data = data_array[:, 8:]   # [GM_Zdd, PM_Zdd, ..., GM_Zqq, PM_Zqq]

    # 工况 key = (Ud, Uq, Id, Iq, kpv, kiv, kpi) 前7列唯一确定一个工况
    conditions         = input_data[:, :7]
    conditions_rounded = np.round(conditions, decimals=3)
    unique_conditions, inverse_indices = np.unique(conditions_rounded, axis=0, return_inverse=True)
    
    num_conditions = len(unique_conditions)
    print(f"唯一工况数量: {num_conditions}")
    
    condition_counts = np.bincount(inverse_indices)
    print(f"每个工况的平均数据点数: {np.mean(condition_counts):.1f}")
    
    np.random.seed(random_seed)
    shuffled_indices = np.random.permutation(num_conditions)
    
    num_train = int(num_conditions * train_ratio)
    num_val = int(num_conditions * val_ratio)
    
    train_condition_idx = shuffled_indices[:num_train]
    val_condition_idx = shuffled_indices[num_train:num_train + num_val]
    test_condition_idx = shuffled_indices[num_train + num_val:]
    
    print(f"\n工况划分: 训练{len(train_condition_idx)}, 验证{len(val_condition_idx)}, 测试{len(test_condition_idx)}")
    
    train_mask = np.isin(inverse_indices, train_condition_idx)
    val_mask = np.isin(inverse_indices, val_condition_idx)
    test_mask = np.isin(inverse_indices, test_condition_idx)
    
    input_train, output_train = input_data[train_mask], output_data[train_mask]
    input_val, output_val = input_data[val_mask], output_data[val_mask]
    input_test, output_test = input_data[test_mask], output_data[test_mask]
    
    print(f"数据点划分: 训练{len(input_train)}, 验证{len(input_val)}, 测试{len(input_test)}")
    
    condition_info = {
        'train_conditions': unique_conditions[train_condition_idx],
        'val_conditions': unique_conditions[val_condition_idx],
        'test_conditions': unique_conditions[test_condition_idx],
    }
    
    return (input_train, output_train), (input_val, output_val), (input_test, output_test), condition_info


def train_model(model, train_data, val_data, config, device):
    """训练模型"""
    print("\n" + "="*60)
    print("开始训练")
    print("="*60)
    
    input_train, output_train = train_data
    input_val, output_val = val_data
    
    model.set_normalization_params(input_train, output_train)
    
    input_train_tensor = torch.tensor(input_train, dtype=torch.float32).to(device)
    output_train_tensor = torch.tensor(output_train, dtype=torch.float32).to(device)
    input_val_tensor = torch.tensor(input_val, dtype=torch.float32).to(device)
    output_val_tensor = torch.tensor(output_val, dtype=torch.float32).to(device)
    
    output_train_normalized = model.normalize_output(output_train_tensor)
    output_val_normalized = model.normalize_output(output_val_tensor)
    
    batch_size = config.get('batch_size', 32)
    train_dataset = TensorDataset(input_train_tensor, output_train_normalized)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.get('initial_lr', 0.001),
        weight_decay=config.get('weight_decay', 1e-4),
        betas=(0.9, 0.98)
    )
    
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.6,
        patience=config.get('patience', 15),
        min_lr=1e-7, verbose=True
    )
    
    criterion = nn.MSELoss()
    num_epochs = config.get('num_epochs', 300)
    
    train_loss_history = []
    val_loss_history = []
    best_val_loss = float('inf')
    best_model_state = None
    
    start_time = time.time()
    
    for epoch in range(num_epochs):
        model.train()
        epoch_train_loss = 0.0
        num_batches = 0
        
        for batch_inputs, batch_outputs_normalized in train_loader:
            optimizer.zero_grad()
            predictions_normalized = model(batch_inputs)
            loss = criterion(predictions_normalized, batch_outputs_normalized)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            epoch_train_loss += loss.item()
            num_batches += 1
        
        avg_train_loss = epoch_train_loss / num_batches
        train_loss_history.append(avg_train_loss)
        
        model.eval()
        with torch.no_grad():
            val_predictions_normalized = model(input_val_tensor)
            val_loss = criterion(val_predictions_normalized, output_val_normalized).item()
            val_loss_history.append(val_loss)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_state = model.state_dict().copy()
            
            scheduler.step(val_loss)
        
        if epoch % 20 == 0 or epoch == num_epochs - 1:
            print(f"Epoch {epoch:3d}/{num_epochs} | Train: {avg_train_loss:.6f} | Val: {val_loss:.6f} | LR: {optimizer.param_groups[0]['lr']:.2e}")
    
    training_time = time.time() - start_time
    print(f"\n训练完成! 耗时: {training_time:.2f}秒, 最佳验证损失: {best_val_loss:.6f}")
    
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    return {
        'train_loss': train_loss_history,
        'val_loss': val_loss_history,
        'best_val_loss': best_val_loss,
        'training_time': training_time
    }


def evaluate_model(model, test_data, device):
    """评估模型"""
    print("\n" + "="*60)
    print("模型评估")
    print("="*60)
    
    input_test, output_test = test_data
    
    model.eval()
    with torch.no_grad():
        input_test_tensor = torch.tensor(input_test, dtype=torch.float32).to(device)
        output_test_tensor = torch.tensor(output_test, dtype=torch.float32).to(device)
        
        predictions_normalized = model(input_test_tensor)
        predictions = model.denormalize_output(predictions_normalized).cpu().numpy()
        output_np = output_test_tensor.cpu().numpy()
    
    output_diff = predictions - output_np
    MAE = np.mean(np.abs(output_diff))
    RMSE = np.sqrt(np.mean(output_diff ** 2))
    MAPE = np.mean(np.abs(output_diff) / (np.abs(output_np) + 1e-8)) * 100
    
    MAE_per_dim = np.mean(np.abs(output_diff), axis=0)
    RMSE_per_dim = np.sqrt(np.mean(output_diff ** 2, axis=0))
    
    print(f"MAE: {MAE:.4f}, RMSE: {RMSE:.4f}, MAPE: {MAPE:.2f}%")
    
    output_names = ['GM_Zdd', 'PM_Zdd', 'GM_Zdq', 'PM_Zdq', 'GM_Zqd', 'PM_Zqd', 'GM_Zqq', 'PM_Zqq']
    print(f"\n{'维度':<10} {'MAE':<10} {'RMSE':<10}")
    for i, name in enumerate(output_names):
        print(f"{name:<10} {MAE_per_dim[i]:<10.4f} {RMSE_per_dim[i]:<10.4f}")
    
    return {
        'MAE': MAE, 'RMSE': RMSE, 'MAPE': MAPE,
        'MAE_per_dim': MAE_per_dim, 'RMSE_per_dim': RMSE_per_dim,
        'predictions': predictions, 'true_values': output_np
    }


def plot_training_history(train_history, save_dir):
    """绘制训练历史"""
    plt.figure(figsize=(12, 5))
    
    epochs = range(1, len(train_history['train_loss']) + 1)
    
    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_history['train_loss'], 'b-', label='Train', linewidth=2)
    plt.plot(epochs, train_history['val_loss'], 'r-', label='Val', linewidth=2)
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.title('Training History')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    
    plt.subplot(1, 2, 2)
    mid = len(epochs) // 2
    plt.plot(epochs[mid:], train_history['train_loss'][mid:], 'b-', label='Train', linewidth=2)
    plt.plot(epochs[mid:], train_history['val_loss'][mid:], 'r-', label='Val', linewidth=2)
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.title('Last 50%')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'training_history.png'), dpi=300, bbox_inches='tight')
    plt.close()


def visualize_condition_prediction(model, val_data, condition_info, f_range, save_dir, device):
    """可视化验证集中某个工况的预测效果"""
    print("\n" + "="*60)
    print("生成工况预测可视化")
    print("="*60)
    
    input_val, output_val = val_data
    val_conditions = condition_info['val_conditions']

    # 从验证集工况中随机选择一个
    random_idx        = np.random.randint(0, len(val_conditions))
    selected_condition = val_conditions[random_idx]
    Ud, Uq, Id, Iq, kpv, kiv, kpi = selected_condition

    print(f"选择验证集工况 [{random_idx+1}/{len(val_conditions)}]: "
          f"Ud={Ud:.1f}V, Uq={Uq:.1f}V, Id={Id:.1f}A, Iq={Iq:.1f}A, "
          f"kpv={kpv:.3f}, kiv={kiv:.1f}, kpi={kpi:.3f}")

    # 找出该工况在验证集中的所有数据点 (匹配前7列)
    tolerance = 1e-2
    condition_mask = (
        (np.abs(input_val[:, 0] - Ud)  < tolerance) &
        (np.abs(input_val[:, 1] - Uq)  < tolerance) &
        (np.abs(input_val[:, 2] - Id)  < tolerance) &
        (np.abs(input_val[:, 3] - Iq)  < tolerance) &
        (np.abs(input_val[:, 4] - kpv) < tolerance) &
        (np.abs(input_val[:, 5] - kiv) < tolerance) &
        (np.abs(input_val[:, 6] - kpi) < tolerance)
    )

    val_condition_inputs  = input_val[condition_mask]
    val_condition_outputs = output_val[condition_mask]

    print(f"该工况在验证集的数据点数: {len(val_condition_inputs)}")

    # 生成频率扫描预测 (固定工况+控制参数, 遍历频率)
    frequencies = np.arange(f_range[0], f_range[1] + 1, 1)
    prediction_inputs = np.zeros((len(frequencies), 8))  # [Ud,Uq,Id,Iq,kpv,kiv,kpi,f]
    prediction_inputs[:, 0] = Ud
    prediction_inputs[:, 1] = Uq
    prediction_inputs[:, 2] = Id
    prediction_inputs[:, 3] = Iq
    prediction_inputs[:, 4] = kpv
    prediction_inputs[:, 5] = kiv
    prediction_inputs[:, 6] = kpi
    prediction_inputs[:, 7] = frequencies
    
    model.eval()
    with torch.no_grad():
        prediction_tensor = torch.tensor(prediction_inputs, dtype=torch.float32).to(device)
        predictions_normalized = model(prediction_tensor)
        predictions = model.denormalize_output(predictions_normalized).cpu().numpy()
    
    output_names = ['GM_Zdd', 'PM_Zdd', 'GM_Zdq', 'PM_Zdq', 'GM_Zqd', 'PM_Zqd', 'GM_Zqq', 'PM_Zqq']
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    
    for i, (ax, output_name) in enumerate(zip(axes, output_names)):
        ax.plot(frequencies, predictions[:, i], 'b-', linewidth=2.5, alpha=0.8, label='Predicted')
        
        if len(val_condition_inputs) > 0:
            val_freqs  = val_condition_inputs[:, 7]   # f 现在在第8列 (index 7)
            val_values = val_condition_outputs[:, i]
            ax.scatter(val_freqs, val_values, color='red', s=100, alpha=0.9, 
                      edgecolors='darkred', linewidths=1.5, label='Validation Data')
            
            errors = []
            for freq, actual_val in zip(val_freqs, val_values):
                freq_idx = np.argmin(np.abs(frequencies - freq))
                pred_val = predictions[freq_idx, i]
                error = abs(pred_val - actual_val)
                errors.append(error)
            
            mean_error = np.mean(errors)
            max_error = np.max(errors)
            
            ax.text(0.02, 0.98, f'Mean Err: {mean_error:.3f}\nMax Err: {max_error:.3f}',
                   transform=ax.transAxes, fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                   verticalalignment='top')
        
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel(output_name)
        ax.set_title(f'{output_name}')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(f_range)
        ax.legend(loc='best')
    
    fig.suptitle(
        f'Condition: Ud={Ud:.1f}V, Uq={Uq:.1f}V, Id={Id:.1f}A, Iq={Iq:.1f}A  |  '
        f'kpv={kpv:.3f}, kiv={kiv:.1f}, kpi={kpi:.3f}',
        fontsize=14, fontweight='bold'
    )
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(os.path.join(save_dir, 'condition_prediction.svg'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"可视化已保存")


def save_results(model, train_history, eval_results, save_dir):
    """保存结果"""
    os.makedirs(save_dir, exist_ok=True)
    
    # 保存完整的模型信息（包括归一化参数）
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'input_mean': model.input_mean,
        'input_std': model.input_std,
        'output_mean': model.output_mean,
        'output_std': model.output_std
    }
    torch.save(checkpoint, os.path.join(save_dir, 'best_model.pth'))
    
    np.savez(os.path.join(save_dir, 'training_history.npz'),
             train_loss=train_history['train_loss'],
             val_loss=train_history['val_loss'],
             best_val_loss=train_history['best_val_loss'],
             training_time=train_history['training_time'])
    
    np.savez(os.path.join(save_dir, 'evaluation_results.npz'),
             MAE=eval_results['MAE'],
             RMSE=eval_results['RMSE'],
             MAPE=eval_results['MAPE'],
             MAE_per_dim=eval_results['MAE_per_dim'],
             RMSE_per_dim=eval_results['RMSE_per_dim'],
             predictions=eval_results['predictions'],
             true_values=eval_results['true_values'])
    
    print(f"\n结果已保存到: {save_dir}")


def main_pipeline(csv_file_path, model_config, train_config, save_dir='./NNTrain_outputs', random_seed=42):
    """主训练流程"""
    print("\n" + "="*60)
    print("PINN-VSG 训练流程")
    print("="*60)
    
    set_seed(random_seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"设备: {device}")
    
    train_data, val_data, test_data, condition_info = load_and_split_by_condition(
        csv_file_path,
        train_ratio=train_config.get('train_ratio', 0.75),
        val_ratio=train_config.get('val_ratio', 0.15),
        random_seed=random_seed
    )
    
    model = PINN_VSG(model_config).to(device)
    arch_info = model.get_architecture_info()
    print(f"\n模型: {arch_info['architecture']}")
    print(f"参数量: {arch_info['total_params']:,}")
    
    train_history = train_model(model, train_data, val_data, train_config, device)
    eval_results = evaluate_model(model, test_data, device)
    
    save_results(model, train_history, eval_results, save_dir)
    plot_training_history(train_history, save_dir)
    
    if train_config.get('enable_visualization', True):
        visualize_condition_prediction(model, val_data, condition_info,
                                      f_range=train_config.get('f_range', [10, 140]),
                                      save_dir=save_dir, device=device)
    
    print("\n" + "="*60)
    print(f"训练完成! MAE: {eval_results['MAE']:.4f}, RMSE: {eval_results['RMSE']:.4f}")
    print("="*60)
    
    return model, os.path.join(save_dir, 'best_model.pth')


if __name__ == "__main__":
    csv_file = "IBR1_General_Admittance_Dataset.csv"

    model_config = {
        'polynomial_neurons': 20,
        'frequency_neurons': 32,
        'filter_neurons': 4,
        'control_neurons': 8,
        'phase_neurons': 4,
        'fusion_neurons': 16,
        'activation': 'tanh'
    }

    train_config = {
        'num_epochs': 500,
        'batch_size': 256,
        'initial_lr': 0.001,
        'weight_decay': 1e-4,
        'patience': 15,
        'train_ratio': 0.75,
        'val_ratio': 0.15,
        'enable_visualization': True,
        'f_range': [5, 130]
    }

    if os.path.exists(csv_file):
        trained_model, model_path = main_pipeline(csv_file, model_config, train_config, './NNTrain_outputs', 42)
        print(f"✅ 模型已保存: {model_path}")
    else:
        print(f"❌ 数据文件 '{csv_file}' 不存在")