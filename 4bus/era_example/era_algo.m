function [Residues, s_poles, sig_values] = era_algo(y_data, dt, n)

    y_data = y_data(:);
    N = length(y_data);

    rows = round(N/3);
    cols = round(N/3);

    H0 = zeros(rows, cols);
    H1 = zeros(rows, cols);

    for i = 1:rows
        for j = 1:cols
            H0(i,j) = y_data(i + j - 1);
            H1(i,j) = y_data(i + j);
        end
    end

    [U, S, V] = svd(H0, "econ");
    sig_values = diag(S);

    if n > length(sig_values)
        warning('Requested order exceeds the available rank. Using the maximum admissible order instead.');
        n = length(sig_values);
    end

    Un = U(:,1:n);
    Sn = S(1:n,1:n);
    Vn = V(:,1:n);

    Sn_sqrt = diag(sqrt(diag(Sn)));
    Sn_sqrt_inv = diag(1 ./ sqrt(diag(Sn)));

    A_hat = Sn_sqrt_inv * Un' * H1 * Vn * Sn_sqrt_inv;
    B_hat = Sn_sqrt * Vn';
    B_hat = B_hat(:,1);

    C_hat = Un * Sn_sqrt;
    C_hat = C_hat(1,:);

    [Psi, Lambda_z] = eig(A_hat);
    lambda_z = diag(Lambda_z);
    s_poles = log(lambda_z) / dt;

    B_tilde = Psi \ B_hat;
    C_tilde = C_hat * Psi;
    Residues = C_tilde.' .* B_tilde;

end
