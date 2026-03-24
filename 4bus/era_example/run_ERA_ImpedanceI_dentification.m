%% 一键式自动化：Simulink 扰动运行 + RC + 陷波器 + 模态截断 ERA 阻抗辨识
clear; close all; clc;

%% 1. 自动化运行 Simulink 模型
model_name = 'x4bus_model';
fprintf('正在加载模型: %s.slx...\n', model_name);
load_system(model_name); % 后台加载模型，提高运行速度

% --- 第一次扰动 ---
fprintf('▶ 开始运行第一次扰动 (t_R=1, t_C=10)...\n');
assignin('base', 't_R', 3);
assignin('base', 't_C', 10);
sim(model_name); % 运行仿真

% 提取第一次运行的数据，并保存为 vi_dq1.mat
try
    temp_data1 = evalin('base', 'vi_dq_temp');
    data_struct(1).raw = temp_data1;
    
    % 重命名并存盘，保持原先的数据结构
    vi_dq = temp_data1; 
    save('vi_dq1.mat', 'vi_dq');
    fprintf('  ✔ 第一次数据已成功提取，并保存至 vi_dq1.mat\n');
catch
    error('在基础工作区未找到 vi_dq_temp，请检查 Simulink 设置。');
end

% --- 第二次扰动 ---
fprintf('▶ 开始运行第二次扰动 (t_R=10, t_C=1)...\n');
assignin('base', 't_R', 10);
assignin('base', 't_C', 3);
sim(model_name); % 运行仿真

% 提取第二次运行的数据，并保存为 vi_dq2.mat
try
    temp_data2 = evalin('base', 'vi_dq_temp');
    data_struct(2).raw = temp_data2;
    
    % 重命名并存盘，保持原先的数据结构
    vi_dq = temp_data2; 
    save('vi_dq2.mat', 'vi_dq');
    fprintf('  ✔ 第二次数据已成功提取，并保存至 vi_dq2.mat\n\n');
catch
    error('在基础工作区未找到 vi_dq_temp，请检查 Simulink 设置。');
end

%% 2. 全局设置与数据准备 (复用原有参数)
% --- 参数定义 ---
target_Fs = 8000;      % 目标采样率 (Hz)
t_start   = 3;      % 扰动开始时间 (s)
t_end     = 4;       % 扰动结束时间 (s)
era_order = 30;        % ERA 辨识阶数

% === [清洗配置 1] 时域陷波器 (Notch Filter) ===
use_notch   = true;              % 开关
notch_freqs = [100, 200, 400];   % 要滤除的频率
notch_Q     = 500;               % Q值建议设低 (1-5)，形成宽陷波，覆盖 PLL 抖动范围

% === [清洗配置 2] 模态截断 (Modal Truncation) ===
use_trunc   = true;              % 开关
kill_freqs  = [100, 200, 400, 500]; % 要截断的极点频率
tol_freq    = 0.5;               % 容差 +/- 10Hz

% --- 频率设置 (横坐标范围) ---
f_start_pow = 0;       % 10^0 = 1 Hz
f_end_pow   = 3;       % 10^4 Hz
freq_points = 1000;
freq_hz = logspace(f_start_pow, f_end_pow, freq_points); 

%% 3. 批量处理：双重清洗 + ERA 辨识
var_names = {'vd', 'vq', 'id', 'iq'};
Results = struct(); 

fprintf('开始处理: 陷波器(Q=%.1f) -> ERA -> 模态截断(Tol=%.1f Hz)...\n', notch_Q, tol_freq);

for ds_idx = 1:2
    t_raw_all = data_struct(ds_idx).raw.Time;
    data_matrix = data_struct(ds_idx).raw.Data;
    
    % 确定时间切片
    if ds_idx == 1
        idx_start = find(t_raw_all >= t_start, 1, "first");
        idx_end = find(t_raw_all <= t_end, 1, "last");
        dt_raw = t_raw_all(2) - t_raw_all(1);
        dt_target = 1 / target_Fs;
        step_size = round(dt_target / dt_raw);
    end
    
    for v_idx = 1:4
        var_name = var_names{v_idx};
        
        % 1. 提取原始数据
        sig_cut = data_matrix(idx_start:step_size:idx_end, v_idx);
        
        % 2. === [第一道防线] 时域陷波器 ===
        sig_processed = sig_cut;
        if use_notch && ~isempty(notch_freqs)
            for nf = notch_freqs
                w0 = nf / (target_Fs / 2); 
                if w0 > 0 && w0 < 1
                    bw = w0 / notch_Q; 
                    [b_notch, a_notch] = iirnotch(w0, bw);
                    % 零相位滤波，防止相位失真
                    sig_processed = filtfilt(b_notch, a_notch, sig_processed);
                end
            end
        end
        
        % 3. 去除稳态偏置
        steady_val = sig_processed(1);
        y_input_era = sig_processed - steady_val;
        
        % 4. 执行 ERA 算法
        [Residues, Poles, ~] = era_algo(y_input_era, dt_target, era_order);
        
        % 5. === [第二道防线] 模态截断 ===
        if use_trunc
            % 计算极点物理频率
            p_freqs = abs(imag(Poles)) / (2*pi);
            keep_idx = true(size(Poles));
            
            for kf = kill_freqs
                % 查找落在黑名单范围内的极点
                bad_ones = abs(p_freqs - kf) < tol_freq;
                if any(bad_ones)
                    keep_idx(bad_ones) = false;
                end
            end
            
            % 执行剔除
            Poles = Poles(keep_idx);
            Residues = Residues(keep_idx);
        end
        
        % 存储最终结果
        Results(ds_idx).(var_name).Residues = Residues;
        Results(ds_idx).(var_name).Poles = Poles;
    end
end
fprintf('双重清洗辨识完成。\n');

%% 4. 计算 ERA 导纳矩阵 Y_ERA(s)
s_vec = 1j * 2 * pi * freq_hz;
Y_ERA = zeros(2, 2, length(s_vec));

for k = 1:length(s_vec)
    s = s_vec(k);
    
    H_vd1 = calc_Hs(s, Results(1).vd); H_vq1 = calc_Hs(s, Results(1).vq);
    H_id1 = calc_Hs(s, Results(1).id); H_iq1 = calc_Hs(s, Results(1).iq);
    
    H_vd2 = calc_Hs(s, Results(2).vd); H_vq2 = calc_Hs(s, Results(2).vq);
    H_id2 = calc_Hs(s, Results(2).id); H_iq2 = calc_Hs(s, Results(2).iq);
    
    Mat_V = [H_vd1, H_vd2; H_vq1, H_vq2];
    Mat_I = [H_id1, H_id2; H_iq1, H_iq2];
    
    if abs(det(Mat_V)) > 1e-10 
        Y_ERA(:,:,k) = -Mat_I / Mat_V;
    else
        Y_ERA(:,:,k) = NaN;
    end
end

%% 5. 计算 理论 导纳矩阵 Y_Ana(s)
fprintf('正在计算 理论 导纳矩阵...\n');
Y_Ana = calculate_analytical_Y(freq_hz);

%% 6. 绘制对比 Bode 图
fprintf('绘制对比结果...\n');

Y_data_era = {squeeze(Y_ERA(1,1,:)), squeeze(Y_ERA(1,2,:)), ...
              squeeze(Y_ERA(2,1,:)), squeeze(Y_ERA(2,2,:))};
Y_data_ana = {squeeze(Y_Ana(1,1,:)), squeeze(Y_Ana(1,2,:)), ...
              squeeze(Y_Ana(2,1,:)), squeeze(Y_Ana(2,2,:))};
titles = {'Y_{dd}', 'Y_{dq}', 'Y_{qd}', 'Y_{qq}'};

figure(1); % 改为figure(1)以防覆盖之前可能存在的手动图
set(gcf, 'Position', [100, 50, 800, 600]); 
t = tiledlayout(4, 2, 'TileSpacing', 'tight', 'Padding', 'compact');

for i = 1:4
    % --- Magnitude ---
    nexttile;
    mag_era = 20 * log10(abs(Y_data_era{i}));
    mag_ana = 20 * log10(abs(Y_data_ana{i}));
    semilogx(freq_hz, mag_era, 'b-', 'LineWidth', 1.5); hold on;
    semilogx(freq_hz, mag_ana, 'r--', 'LineWidth', 1.5);
    grid on; xlim([freq_hz(1), freq_hz(end)]); ylabel('Mag (dB)');
    title([titles{i} ' - Magnitude']);
    if i == 1, legend('ERA (Dual-Cleaned)', 'Analytical', 'Location', 'best'); end
    
    % --- Phase ---
    nexttile;
    ph_era = rad2deg(angle(Y_data_era{i}));
    ph_ana = rad2deg(angle(Y_data_ana{i}));
    semilogx(freq_hz, ph_era, 'b-', 'LineWidth', 1.5); hold on;
    semilogx(freq_hz, ph_ana, 'r--', 'LineWidth', 1.5);
    grid on; xlim([freq_hz(1), freq_hz(end)]);
    ylim([-200 200]); yticks(-180:90:180); ylabel('Phase (deg)');
    title([titles{i} ' - Phase']);
end
xlabel(t, 'Frequency (Hz)', 'FontSize', 12);
fprintf('绘图完成。\n');

%% --- 辅助函数 ---

function val = calc_Hs(s, struct_data)
    if isempty(struct_data.Poles)
        val = 0; % 防止全部极点都被截断导致报错
    else
        val = s * sum(struct_data.Residues ./ (s - struct_data.Poles));
    end
end

function Y_total = calculate_analytical_Y(f_vec)
    % 理论参数保持不变
    Lf = 3.2e-3; Cf = 50e-6; Rf = 0.05; Rcf = 0.8;
    w0 = 100*pi; Ts = 1/1e4/2.5;
    Ud = 312; Uq = -136.5; Id = 178.6; Iq = -80.4;   
    J = 0.081; Dq = 3.2154e+03; K = 7.1; Dp = 1.5915e+04;
    kpv = 0.4; kiv = 90; kpi = 11; kii = 0;
    Rv = 0.6; Lv = 3.2e-3; kpwm = 1;
    
    Y_total = zeros(2, 2, length(f_vec));
    for n = 1:length(f_vec)
        fp = f_vec(n);
        w = 2*pi*fp;
        s = 1j*w; 
        
        ZL = [s*Lf+Rf, -w0*Lf; w0*Lf, s*Lf+Rf];   
        GLw = [-Lf*Iq; Lf*Id];
        Gp1 = 1.5*[Ud Uq]; Gp2 = 1.5*[Id Iq];      
        Gq1 = 1.5*[Uq -Ud]; Gq2 = 1.5*[-Iq Id];
        
        M = -1/s/(J*s + Dp)/w0;
        Gtheta1 = M*Gp1; Gtheta2 = M*Gp2;
        Gw1 = Gtheta1 * 0; Gw2 = Gtheta2 * 0; 
        
        GEm1 = 1/(K*s)*(-Gq1); 
        GEm2 = 1/(K*s)*(-Gq2-[Dq 0]);
        
        Hv = kpv + kiv/s; Hi = kpi + kii/s;
        Gd = exp(-1.5*s*Ts);
        Gvird = [-Rv w0*Lv]; Gvirq = [-w0*Lv -Rv];
        
        Gemd1 = Hv*Hi*Gvird + Hv*Hi*GEm1 + [-Hi -w0*Lf]; 
        Gemd2 = Hv*Hi*GEm2 + [-Hv*Hi -Hi*w0*Cf];
        Gemq1 = Hv*Hi*Gvirq + [w0*Lf -Hi]; 
        Gemq2 = [Hi*w0*Cf -Hv*Hi];
        
        Gidq = kpwm*Gd*[Gemd1; Gemq1];
        Gudq = kpwm*Gd*[Gemd2; Gemq2];
        B = Gudq - eye(2) - GLw*Gw2;
        A = (ZL - Gidq + GLw*Gw1);
        ZVSG0 = -inv(B)*A;
        
        Ai = [Iq; -Id]*Gtheta1 + eye(2); Bi = [Iq; -Id]*Gtheta2;
        Au = [Uq; -Ud]*Gtheta1; Bu = [Uq; -Ud]*Gtheta2 + eye(2);
        ZVSG1 = (Au + Bu*ZVSG0) / (Ai + Bi*ZVSG0); 
        
        Zc = inv([s*Cf, -w0*Cf; w0*Cf, s*Cf]) * [1+Rcf*Cf*s, -Rcf*Cf*w0; Rcf*Cf*w0, 1+Rcf*Cf*s];
        ZVSG = inv(inv(Zc) + inv(ZVSG1)); 
        
        Y_total(:,:,n) = inv(ZVSG);
    end
end