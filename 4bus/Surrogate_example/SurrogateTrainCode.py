import copy
import os
import random
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset


OUTPUT_NAMES = [
    "GM_Zdd", "PM_Zdd",
    "GM_Zdq", "PM_Zdq",
    "GM_Zqd", "PM_Zqd",
    "GM_Zqq", "PM_Zqq",
]


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class PINN_VSG(nn.Module):
    def __init__(self, config):
        super().__init__()

        self.poly_neurons = config.get("polynomial_neurons", 20)
        self.freq_neurons = config.get("frequency_neurons", 32)
        self.filter_neurons = config.get("filter_neurons", 4)
        self.control_neurons = config.get("control_neurons", 8)
        self.phase_neurons = config.get("phase_neurons", 4)
        self.fusion_neurons = config.get("fusion_neurons", 16)

        self.input_mean = None
        self.input_std = None
        self.output_mean = None
        self.output_std = None

        self.activation = self._get_activation(config.get("activation", "tanh"))

        self.branch1 = nn.Linear(4, self.poly_neurons)

        self.branch2 = nn.Sequential(
            nn.Linear(4, self.freq_neurons),
            self.activation,
        )

        self.head_filter = nn.Sequential(
            nn.Linear(self.freq_neurons, self.filter_neurons),
            self.activation,
        )
        self.head_control = nn.Sequential(
            nn.Linear(self.freq_neurons, self.control_neurons),
            self.activation,
        )
        self.head_phase = nn.Sequential(
            nn.Linear(self.freq_neurons, self.phase_neurons),
            self.activation,
        )

        fusion_dim = (
            self.poly_neurons
            + self.filter_neurons
            + self.control_neurons
            + self.phase_neurons
        )

        self.fusion = nn.Sequential(
            nn.Linear(fusion_dim, self.fusion_neurons),
            self.activation,
        )

        self.output_layer = nn.Linear(self.fusion_neurons, 8)
        self._initialize_weights()

    @staticmethod
    def _get_activation(name):
        mapping = {
            "sigmoid": nn.Sigmoid(),
            "relu": nn.ReLU(),
            "tanh": nn.Tanh(),
            "leaky_relu": nn.LeakyReLU(),
            "linear": nn.Identity(),
        }
        return mapping.get(str(name).lower(), nn.Tanh())

    def _initialize_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0.0)

    def set_normalization_params(self, input_data, output_data):
        self.input_mean = torch.tensor(np.mean(input_data, axis=0), dtype=torch.float32)
        self.input_std = torch.tensor(np.std(input_data, axis=0), dtype=torch.float32)
        self.output_mean = torch.tensor(np.mean(output_data, axis=0), dtype=torch.float32)
        self.output_std = torch.tensor(np.std(output_data, axis=0), dtype=torch.float32)

    def normalize_input(self, x):
        if self.input_mean is None:
            return x
        device = x.device
        return (x - self.input_mean.to(device)) / (self.input_std.to(device) + 1e-8)

    def normalize_output(self, y):
        if self.output_mean is None:
            return y
        device = y.device
        return (y - self.output_mean.to(device)) / (self.output_std.to(device) + 1e-8)

    def denormalize_output(self, y):
        if self.output_mean is None:
            return y
        device = y.device
        return y * (self.output_std.to(device) + 1e-8) + self.output_mean.to(device)

    def forward(self, x):
        x = self.normalize_input(x)

        operating_points = x[:, :4]
        freq_ctrl = x[:, 4:8]

        poly_features = self.branch1(operating_points)
        freq_features = self.branch2(freq_ctrl)

        filter_features = self.head_filter(freq_features)
        control_features = self.head_control(freq_features)
        phase_features = self.head_phase(freq_features)

        features = torch.cat(
            [poly_features, filter_features, control_features, phase_features],
            dim=1,
        )

        features = self.fusion(features)
        return self.output_layer(features)

    def get_architecture_info(self):
        total_params = sum(p.numel() for p in self.parameters())
        fusion_dim = (
            self.poly_neurons
            + self.filter_neurons
            + self.control_neurons
            + self.phase_neurons
        )
        arch = (
            f"4->{self.poly_neurons} | "
            f"4->{self.freq_neurons}->"
            f"[{self.filter_neurons},{self.control_neurons},{self.phase_neurons}] | "
            f"{fusion_dim}->{self.fusion_neurons}->8"
        )
        return {
            "model_type": "PINN_VSG",
            "total_params": total_params,
            "architecture": arch,
        }


def load_and_split_by_condition(csv_file_path, train_ratio=0.75, val_ratio=0.15, random_seed=42):
    data = pd.read_csv(csv_file_path, header=0)
    data_array = np.asarray(data, dtype=np.float32)

    input_data = data_array[:, :8]
    output_data = data_array[:, 8:]

    conditions = np.round(input_data[:, :7], decimals=3)
    unique_conditions, inverse_indices = np.unique(
        conditions, axis=0, return_inverse=True
    )

    num_conditions = len(unique_conditions)
    counts = np.bincount(inverse_indices)

    rng = np.random.default_rng(random_seed)
    shuffled = rng.permutation(num_conditions)

    num_train = int(num_conditions * train_ratio)
    num_val = int(num_conditions * val_ratio)

    train_condition_idx = shuffled[:num_train]
    val_condition_idx = shuffled[num_train:num_train + num_val]
    test_condition_idx = shuffled[num_train + num_val:]

    train_mask = np.isin(inverse_indices, train_condition_idx)
    val_mask = np.isin(inverse_indices, val_condition_idx)
    test_mask = np.isin(inverse_indices, test_condition_idx)

    input_train, output_train = input_data[train_mask], output_data[train_mask]
    input_val, output_val = input_data[val_mask], output_data[val_mask]
    input_test, output_test = input_data[test_mask], output_data[test_mask]

    print(f"Loaded: {csv_file_path}")
    print(f"Shape: {data.shape}")
    print(f"Conditions: {num_conditions}")
    print(f"Avg. samples/condition: {np.mean(counts):.1f}")
    print(
        f"Split by condition -> "
        f"train: {len(train_condition_idx)}, "
        f"val: {len(val_condition_idx)}, "
        f"test: {len(test_condition_idx)}"
    )
    print(
        f"Samples -> "
        f"train: {len(input_train)}, "
        f"val: {len(input_val)}, "
        f"test: {len(input_test)}"
    )

    condition_info = {
        "train_conditions": unique_conditions[train_condition_idx],
        "val_conditions": unique_conditions[val_condition_idx],
        "test_conditions": unique_conditions[test_condition_idx],
    }

    return (
        (input_train, output_train),
        (input_val, output_val),
        (input_test, output_test),
        condition_info,
    )


def train_model(model, train_data, val_data, config, device):
    input_train, output_train = train_data
    input_val, output_val = val_data

    model.set_normalization_params(input_train, output_train)

    input_train_tensor = torch.tensor(input_train, dtype=torch.float32, device=device)
    output_train_tensor = torch.tensor(output_train, dtype=torch.float32, device=device)
    input_val_tensor = torch.tensor(input_val, dtype=torch.float32, device=device)
    output_val_tensor = torch.tensor(output_val, dtype=torch.float32, device=device)

    output_train_norm = model.normalize_output(output_train_tensor)
    output_val_norm = model.normalize_output(output_val_tensor)

    batch_size = config.get("batch_size", 32)
    train_dataset = TensorDataset(input_train_tensor, output_train_norm)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.get("initial_lr", 1e-3),
        weight_decay=config.get("weight_decay", 1e-4),
        betas=(0.9, 0.98),
    )

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.6,
        patience=config.get("patience", 15),
        min_lr=1e-7,
        verbose=True,
    )

    criterion = nn.MSELoss()
    num_epochs = config.get("num_epochs", 300)

    train_loss_history = []
    val_loss_history = []
    best_val_loss = float("inf")
    best_model_state = None

    start_time = time.time()

    for epoch in range(num_epochs):
        model.train()
        epoch_loss = 0.0
        num_batches = 0

        for batch_inputs, batch_targets in train_loader:
            optimizer.zero_grad()
            pred = model(batch_inputs)
            loss = criterion(pred, batch_targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += loss.item()
            num_batches += 1

        train_loss = epoch_loss / max(num_batches, 1)
        train_loss_history.append(train_loss)

        model.eval()
        with torch.no_grad():
            val_pred = model(input_val_tensor)
            val_loss = criterion(val_pred, output_val_norm).item()

        val_loss_history.append(val_loss)
        scheduler.step(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = copy.deepcopy(model.state_dict())

        if epoch % 20 == 0 or epoch == num_epochs - 1:
            lr = optimizer.param_groups[0]["lr"]
            print(
                f"Epoch {epoch:3d}/{num_epochs} | "
                f"train {train_loss:.6f} | "
                f"val {val_loss:.6f} | "
                f"lr {lr:.2e}"
            )

    training_time = time.time() - start_time

    if best_model_state is not None:
        model.load_state_dict(best_model_state)

    print(
        f"Training finished in {training_time:.2f}s | "
        f"best val loss: {best_val_loss:.6f}"
    )

    return {
        "train_loss": train_loss_history,
        "val_loss": val_loss_history,
        "best_val_loss": best_val_loss,
        "training_time": training_time,
    }


def evaluate_model(model, test_data, device):
    input_test, output_test = test_data

    model.eval()
    with torch.no_grad():
        input_test_tensor = torch.tensor(input_test, dtype=torch.float32, device=device)
        output_test_tensor = torch.tensor(output_test, dtype=torch.float32, device=device)

        pred_norm = model(input_test_tensor)
        predictions = model.denormalize_output(pred_norm).cpu().numpy()
        targets = output_test_tensor.cpu().numpy()

    diff = predictions - targets

    mae = np.mean(np.abs(diff))
    rmse = np.sqrt(np.mean(diff ** 2))
    mape = np.mean(np.abs(diff) / (np.abs(targets) + 1e-8)) * 100.0

    mae_per_dim = np.mean(np.abs(diff), axis=0)
    rmse_per_dim = np.sqrt(np.mean(diff ** 2, axis=0))

    print(f"Test -> MAE: {mae:.4f}, RMSE: {rmse:.4f}, MAPE: {mape:.2f}%")
    print(f"\n{'Output':<10} {'MAE':<10} {'RMSE':<10}")
    for name, mae_i, rmse_i in zip(OUTPUT_NAMES, mae_per_dim, rmse_per_dim):
        print(f"{name:<10} {mae_i:<10.4f} {rmse_i:<10.4f}")

    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "MAE_per_dim": mae_per_dim,
        "RMSE_per_dim": rmse_per_dim,
        "predictions": predictions,
        "true_values": targets,
    }


def plot_training_history(train_history, save_dir):
    plt.figure(figsize=(12, 5))

    epochs = range(1, len(train_history["train_loss"]) + 1)

    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_history["train_loss"], label="Train", linewidth=2)
    plt.plot(epochs, train_history["val_loss"], label="Val", linewidth=2)
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.title("Training History")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.yscale("log")

    plt.subplot(1, 2, 2)
    mid = len(train_history["train_loss"]) // 2
    plt.plot(list(epochs)[mid:], train_history["train_loss"][mid:], label="Train", linewidth=2)
    plt.plot(list(epochs)[mid:], train_history["val_loss"][mid:], label="Val", linewidth=2)
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.title("Last 50%")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.yscale("log")

    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, "training_history.png"), dpi=300, bbox_inches="tight")
    plt.close()


def visualize_condition_prediction(model, val_data, condition_info, f_range, save_dir, device):
    input_val, output_val = val_data
    val_conditions = condition_info["val_conditions"]

    random_idx = np.random.randint(0, len(val_conditions))
    selected_condition = val_conditions[random_idx]
    Ud, Uq, Id, Iq, kpv, kiv, kpi = selected_condition

    print(
        f"Validation condition {random_idx + 1}/{len(val_conditions)}: "
        f"Ud={Ud:.1f}, Uq={Uq:.1f}, Id={Id:.1f}, Iq={Iq:.1f}, "
        f"kpv={kpv:.3f}, kiv={kiv:.1f}, kpi={kpi:.3f}"
    )

    tol = 1e-2
    condition_mask = (
        (np.abs(input_val[:, 0] - Ud) < tol)
        & (np.abs(input_val[:, 1] - Uq) < tol)
        & (np.abs(input_val[:, 2] - Id) < tol)
        & (np.abs(input_val[:, 3] - Iq) < tol)
        & (np.abs(input_val[:, 4] - kpv) < tol)
        & (np.abs(input_val[:, 5] - kiv) < tol)
        & (np.abs(input_val[:, 6] - kpi) < tol)
    )

    val_condition_inputs = input_val[condition_mask]
    val_condition_outputs = output_val[condition_mask]

    frequencies = np.arange(f_range[0], f_range[1] + 1, 1)
    prediction_inputs = np.zeros((len(frequencies), 8), dtype=np.float32)
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
        prediction_tensor = torch.tensor(prediction_inputs, dtype=torch.float32, device=device)
        pred_norm = model(prediction_tensor)
        predictions = model.denormalize_output(pred_norm).cpu().numpy()

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()

    for i, (ax, output_name) in enumerate(zip(axes, OUTPUT_NAMES)):
        ax.plot(frequencies, predictions[:, i], linewidth=2.5, alpha=0.85, label="Prediction")

        if len(val_condition_inputs) > 0:
            val_freqs = val_condition_inputs[:, 7]
            val_values = val_condition_outputs[:, i]

            ax.scatter(
                val_freqs,
                val_values,
                s=100,
                alpha=0.9,
                edgecolors="darkred",
                linewidths=1.5,
                label="Validation",
            )

            errors = []
            for freq, actual_val in zip(val_freqs, val_values):
                freq_idx = np.argmin(np.abs(frequencies - freq))
                pred_val = predictions[freq_idx, i]
                errors.append(abs(pred_val - actual_val))

            mean_error = np.mean(errors)
            max_error = np.max(errors)

            ax.text(
                0.02,
                0.98,
                f"Mean Err: {mean_error:.3f}\nMax Err: {max_error:.3f}",
                transform=ax.transAxes,
                fontsize=9,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="yellow", alpha=0.7),
                verticalalignment="top",
            )

        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel(output_name)
        ax.set_title(output_name)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(f_range)
        ax.legend(loc="best")

    fig.suptitle(
        f"Ud={Ud:.1f} V, Uq={Uq:.1f} V, Id={Id:.1f} A, Iq={Iq:.1f} A | "
        f"kpv={kpv:.3f}, kiv={kiv:.1f}, kpi={kpi:.3f}",
        fontsize=14,
        fontweight="bold",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(os.path.join(save_dir, "condition_prediction.svg"), dpi=300, bbox_inches="tight")
    plt.close()

    print("Saved condition_prediction.svg")


def save_results(model, train_history, eval_results, save_dir):
    os.makedirs(save_dir, exist_ok=True)

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "input_mean": model.input_mean,
        "input_std": model.input_std,
        "output_mean": model.output_mean,
        "output_std": model.output_std,
    }
    torch.save(checkpoint, os.path.join(save_dir, "best_model.pth"))

    np.savez(
        os.path.join(save_dir, "training_history.npz"),
        train_loss=train_history["train_loss"],
        val_loss=train_history["val_loss"],
        best_val_loss=train_history["best_val_loss"],
        training_time=train_history["training_time"],
    )

    np.savez(
        os.path.join(save_dir, "evaluation_results.npz"),
        MAE=eval_results["MAE"],
        RMSE=eval_results["RMSE"],
        MAPE=eval_results["MAPE"],
        MAE_per_dim=eval_results["MAE_per_dim"],
        RMSE_per_dim=eval_results["RMSE_per_dim"],
        predictions=eval_results["predictions"],
        true_values=eval_results["true_values"],
    )

    print(f"Saved results to: {save_dir}")


def main_pipeline(
    csv_file_path,
    model_config,
    train_config,
    save_dir="./NNTrain_outputs",
    random_seed=42,
):
    set_seed(random_seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_data, val_data, test_data, condition_info = load_and_split_by_condition(
        csv_file_path,
        train_ratio=train_config.get("train_ratio", 0.75),
        val_ratio=train_config.get("val_ratio", 0.15),
        random_seed=random_seed,
    )

    model = PINN_VSG(model_config).to(device)
    arch_info = model.get_architecture_info()
    print(f"Model: {arch_info['architecture']}")
    print(f"Parameters: {arch_info['total_params']:,}")

    train_history = train_model(model, train_data, val_data, train_config, device)
    eval_results = evaluate_model(model, test_data, device)

    save_results(model, train_history, eval_results, save_dir)
    plot_training_history(train_history, save_dir)

    if train_config.get("enable_visualization", True):
        visualize_condition_prediction(
            model,
            val_data,
            condition_info,
            f_range=train_config.get("f_range", [10, 140]),
            save_dir=save_dir,
            device=device,
        )

    print(
        f"Finished | MAE: {eval_results['MAE']:.4f}, "
        f"RMSE: {eval_results['RMSE']:.4f}"
    )

    return model, os.path.join(save_dir, "best_model.pth")


if __name__ == "__main__":
    csv_file = "IBR1_General_Admittance_Dataset.csv"

    model_config = {
        "polynomial_neurons": 20,
        "frequency_neurons": 32,
        "filter_neurons": 4,
        "control_neurons": 8,
        "phase_neurons": 4,
        "fusion_neurons": 16,
        "activation": "tanh",
    }

    train_config = {
        "num_epochs": 500,
        "batch_size": 256,
        "initial_lr": 1e-3,
        "weight_decay": 1e-4,
        "patience": 15,
        "train_ratio": 0.75,
        "val_ratio": 0.15,
        "enable_visualization": True,
        "f_range": [5, 130],
    }

    if os.path.exists(csv_file):
        _, model_path = main_pipeline(
            csv_file,
            model_config,
            train_config,
            "./NNTrain_outputs",
            42,
        )
        print(f"Model saved to: {model_path}")
    else:
        print(f"Missing file: {csv_file}")
