function [Residues, s_poles, sig_values] = era_algo(y_data, dt, n)
% ERA_ALGO Eigensystem Realization Algorithm (ERA) 封装函数
%
% 输入:
%   y_data: 去除稳态后的暂态数据 (列向量)
%   dt:     采样时间 (s)
%   n:      目标系统阶数 (Order)
%
% 输出:
%   Residues:   极点对应的留数 (复数向量)
%   s_poles:    识别出的连续域极点 (复数向量)
%   sig_values: SVD 分解的奇异值 (用于判断阶数是否合理)

    %% 1. 数据预处理
    y_data = y_data(:); % 强制转换为列向量
    N = length(y_data);
    
    %% 2. 构建 Hankel 矩阵
    % 按照原逻辑，取数据长度的约 1/3 构建矩阵维度
    Rows = round(N/3);
    Cols = round(N/3);
    
    H0 = zeros(Rows, Cols);
    H1 = zeros(Rows, Cols);
    
    % 构建 H0 和 H1 (对应 k 和 k+1)
    for r = 1:Rows
        for c = 1:Cols
            H0(r,c) = y_data(r+c-1);
            H1(r,c) = y_data(r+c);
        end
    end
    
    %% 3. SVD 分解
    [U, S, V] = svd(H0, "econ");
    sig_values = diag(S);
    
    %% 4. 截断与模型降阶
    % 如果输入的 n 大于可用的奇异值数量，进行限制
    if n > length(sig_values)
        warning('请求的阶数 n 大于 Hankel 矩阵的秩，已自动调整为最大秩。');
        n = length(sig_values);
    end

    Un = U(:, 1:n);
    Sn = S(1:n, 1:n);
    Vn = V(:, 1:n);
    
    %% 5. 提取系统矩阵 (A, B, C)
    Sn_sqrt = diag(sqrt(diag(Sn)));
    Sn_sqrt_inv = diag(1 ./ sqrt(diag(Sn)));
    
    % 计算离散域系统矩阵
    A_hat = Sn_sqrt_inv * Un' * H1 * Vn * Sn_sqrt_inv;
    
    % B_hat 和 C_hat
    B_hat = Sn_sqrt * Vn'; 
    B_hat = B_hat(:, 1); % 取第一列
    
    C_hat = Un * Sn_sqrt; 
    C_hat = C_hat(1, :); % 取第一行
    
    %% 6. 模态参数识别 (极点与留数)
    [Psi, Lambda_z_matrix] = eig(A_hat);
    lambda_z = diag(Lambda_z_matrix);
    
    % 转换到连续域 s 平面
    s_poles = log(lambda_z) / dt;
    
    % 计算留数 (Residues)
    % 原始逻辑: Residues = (C * Psi).' .* (Psi \ B)
    B_tilde = Psi \ B_hat;      
    C_tilde = C_hat * Psi;
    Residues = (C_tilde.' .* B_tilde); 
    
end