clear; close all; clc;

model_name = 'x4bus_model';
fprintf('Loading %s.slx...\n', model_name);
load_system(model_name);

data_struct = struct();

fprintf('Run 1: t_R = 3, t_C = 10\n');
assignin('base', 't_R', 3);
assignin('base', 't_C', 10);
sim(model_name);

try
    temp_data = evalin('base', 'vi_dq_temp');
    data_struct(1).raw = temp_data;
    vi_dq = temp_data;
    save('vi_dq1.mat', 'vi_dq');
catch
    error('Variable "vi_dq_temp" was not found in the base workspace.');
end

fprintf('Run 2: t_R = 10, t_C = 3\n');
assignin('base', 't_R', 10);
assignin('base', 't_C', 3);
sim(model_name);

try
    temp_data = evalin('base', 'vi_dq_temp');
    data_struct(2).raw = temp_data;
    vi_dq = temp_data;
    save('vi_dq2.mat', 'vi_dq');
catch
    error('Variable "vi_dq_temp" was not found in the base workspace.');
end

target_fs = 8000;
t_start = 3;
t_end = 4;
era_order = 30;

use_notch = true;
notch_freqs = [100, 200, 400];
notch_q = 500;

use_trunc = true;
reject_freqs = [100, 200, 400, 500];
freq_tol = 0.5;

freq_hz = logspace(0, 3, 1000);

var_names = {'vd', 'vq', 'id', 'iq'};
Results = struct();

fprintf('Running ERA identification...\n');

for ds_idx = 1:2
    t_raw = data_struct(ds_idx).raw.Time;
    data_matrix = data_struct(ds_idx).raw.Data;

    idx_start = find(t_raw >= t_start, 1, 'first');
    idx_end = find(t_raw <= t_end, 1, 'last');

    dt_raw = t_raw(2) - t_raw(1);
    dt_target = 1 / target_fs;
    step_size = round(dt_target / dt_raw);

    for v_idx = 1:4
        var_name = var_names{v_idx};
        sig = data_matrix(idx_start:step_size:idx_end, v_idx);

        if use_notch && ~isempty(notch_freqs)
            for nf = notch_freqs
                w0 = nf / (target_fs / 2);
                if w0 > 0 && w0 < 1
                    bw = w0 / notch_q;
                    [b_notch, a_notch] = iirnotch(w0, bw);
                    sig = filtfilt(b_notch, a_notch, sig);
                end
            end
        end

        y_input_era = sig - sig(1);
        [Residues, Poles, ~] = era_algo(y_input_era, dt_target, era_order);

        if use_trunc
            pole_freqs = abs(imag(Poles)) / (2 * pi);
            keep_idx = true(size(Poles));

            for rf = reject_freqs
                keep_idx(abs(pole_freqs - rf) < freq_tol) = false;
            end

            Poles = Poles(keep_idx);
            Residues = Residues(keep_idx);
        end

        Results(ds_idx).(var_name).Residues = Residues;
        Results(ds_idx).(var_name).Poles = Poles;
    end
end

fprintf('ERA identification finished.\n');

s_vec = 1j * 2 * pi * freq_hz;
Y_ERA = zeros(2, 2, length(s_vec));

for k = 1:length(s_vec)
    s = s_vec(k);

    H_vd1 = calc_Hs(s, Results(1).vd);
    H_vq1 = calc_Hs(s, Results(1).vq);
    H_id1 = calc_Hs(s, Results(1).id);
    H_iq1 = calc_Hs(s, Results(1).iq);

    H_vd2 = calc_Hs(s, Results(2).vd);
    H_vq2 = calc_Hs(s, Results(2).vq);
    H_id2 = calc_Hs(s, Results(2).id);
    H_iq2 = calc_Hs(s, Results(2).iq);

    Mat_V = [H_vd1, H_vd2; H_vq1, H_vq2];
    Mat_I = [H_id1, H_id2; H_iq1, H_iq2];

    if abs(det(Mat_V)) > 1e-10
        Y_ERA(:, :, k) = -Mat_I / Mat_V;
    else
        Y_ERA(:, :, k) = NaN;
    end
end

fprintf('Computing analytical admittance...\n');
Y_Ana = calculate_analytical_Y(freq_hz);

fprintf('Plotting...\n');

Y_data_era = {
    squeeze(Y_ERA(1,1,:)), squeeze(Y_ERA(1,2,:)), ...
    squeeze(Y_ERA(2,1,:)), squeeze(Y_ERA(2,2,:))
};

Y_data_ana = {
    squeeze(Y_Ana(1,1,:)), squeeze(Y_Ana(1,2,:)), ...
    squeeze(Y_Ana(2,1,:)), squeeze(Y_Ana(2,2,:))
};

titles = {'Y_{dd}', 'Y_{dq}', 'Y_{qd}', 'Y_{qq}'};

figure(1);
set(gcf, 'Position', [100, 50, 800, 600]);

t = tiledlayout(4, 2, 'TileSpacing', 'tight', 'Padding', 'compact');

for i = 1:4
    nexttile;
    mag_era = 20 * log10(abs(Y_data_era{i}));
    mag_ana = 20 * log10(abs(Y_data_ana{i}));
    semilogx(freq_hz, mag_era, 'b-', 'LineWidth', 1.5);
    hold on;
    semilogx(freq_hz, mag_ana, 'r--', 'LineWidth', 1.5);
    grid on;
    xlim([freq_hz(1), freq_hz(end)]);
    ylabel('Mag (dB)');
    title([titles{i} ' - Magnitude']);
    if i == 1
        legend('ERA', 'Analytical', 'Location', 'best');
    end

    nexttile;
    ph_era = rad2deg(angle(Y_data_era{i}));
    ph_ana = rad2deg(angle(Y_data_ana{i}));
    semilogx(freq_hz, ph_era, 'b-', 'LineWidth', 1.5);
    hold on;
    semilogx(freq_hz, ph_ana, 'r--', 'LineWidth', 1.5);
    grid on;
    xlim([freq_hz(1), freq_hz(end)]);
    ylim([-200 200]);
    yticks(-180:90:180);
    ylabel('Phase (deg)');
    title([titles{i} ' - Phase']);
end

xlabel(t, 'Frequency (Hz)', 'FontSize', 12);
fprintf('Done.\n');

function val = calc_Hs(s, struct_data)
    if isempty(struct_data.Poles)
        val = 0;
    else
        val = s * sum(struct_data.Residues ./ (s - struct_data.Poles));
    end
end

function Y_total = calculate_analytical_Y(f_vec)

    Lf = 3.2e-3;
    Cf = 50e-6;
    Rf = 0.05;
    Rcf = 0.8;
    w0 = 100*pi;
    Ts = 1/1e4/2.5;

    Ud = 312;
    Uq = -136.5;
    Id = 178.6;
    Iq = -80.4;

    J = 0.081;
    Dq = 3.2154e+03;
    K = 7.1;
    Dp = 1.5915e+04;

    kpv = 0.4;
    kiv = 90;
    kpi = 11;
    kii = 0;

    Rv = 0.6;
    Lv = 3.2e-3;
    kpwm = 1;

    Y_total = zeros(2, 2, length(f_vec));

    for n = 1:length(f_vec)
        fp = f_vec(n);
        w = 2*pi*fp;
        s = 1j*w;

        ZL = [s*Lf+Rf, -w0*Lf; w0*Lf, s*Lf+Rf];
        GLw = [-Lf*Iq; Lf*Id];

        Gp1 = 1.5*[Ud Uq];
        Gp2 = 1.5*[Id Iq];
        Gq1 = 1.5*[Uq -Ud];
        Gq2 = 1.5*[-Iq Id];

        M = -1/s/(J*s + Dp)/w0;
        Gtheta1 = M*Gp1;
        Gtheta2 = M*Gp2;
        Gw1 = Gtheta1 * 0;
        Gw2 = Gtheta2 * 0;

        GEm1 = 1/(K*s)*(-Gq1);
        GEm2 = 1/(K*s)*(-Gq2-[Dq 0]);

        Hv = kpv + kiv/s;
        Hi = kpi + kii/s;
        Gd = exp(-1.5*s*Ts);

        Gvird = [-Rv w0*Lv];
        Gvirq = [-w0*Lv -Rv];

        Gemd1 = Hv*Hi*Gvird + Hv*Hi*GEm1 + [-Hi -w0*Lf];
        Gemd2 = Hv*Hi*GEm2 + [-Hv*Hi -Hi*w0*Cf];
        Gemq1 = Hv*Hi*Gvirq + [w0*Lf -Hi];
        Gemq2 = [Hi*w0*Cf -Hv*Hi];

        Gidq = kpwm*Gd*[Gemd1; Gemq1];
        Gudq = kpwm*Gd*[Gemd2; Gemq2];

        B = Gudq - eye(2) - GLw*Gw2;
        A = ZL - Gidq + GLw*Gw1;

        ZVSG0 = -inv(B) * A;

        Ai = [Iq; -Id]*Gtheta1 + eye(2);
        Bi = [Iq; -Id]*Gtheta2;
        Au = [Uq; -Ud]*Gtheta1;
        Bu = [Uq; -Ud]*Gtheta2 + eye(2);

        ZVSG1 = (Au + Bu*ZVSG0) / (Ai + Bi*ZVSG0);
        Zc = inv([s*Cf, -w0*Cf; w0*Cf, s*Cf]) * ...
             [1+Rcf*Cf*s, -Rcf*Cf*w0; Rcf*Cf*w0, 1+Rcf*Cf*s];

        ZVSG = inv(inv(Zc) + inv(ZVSG1));
        Y_total(:, :, n) = inv(ZVSG);
    end
end
