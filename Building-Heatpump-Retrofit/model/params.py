"""40 kW R290 monobloc module (one of four in cascade)."""
MODULE = dict(
    fluid="Propane",
    comp=dict(disp_m3h=36.0, f_nom=50, f_min=25, f_max=110, eta_is_max=0.70, pr_opt=3.2, k_pr=0.09, k_f=0.08,
              f_opt=60, clearance=0.03, n_poly=1.12, leak=0.03, eta_motor=0.93, eta_inv=0.97, q_loss_frac=0.05),
    m_air_nom=3.4, UA_e=7000.0, fan_min=0.35, W_fan_max=1100.0,
    m_w=1.3, UA_c=6500.0, SH=5.0, SC=3.0, suction_gain=1.0,
    dp_suc=0.05e5, dp_evap=0.10e5, dp_cond=0.08e5, dp_dis=0.06e5, T_dis_max=125.0,
)
