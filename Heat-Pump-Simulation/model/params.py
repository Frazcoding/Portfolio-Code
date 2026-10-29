"""Design parameters for the 45 kW two-stage R290 air-source heat pump."""
LP = dict(disp_m3h=2 * 21.0, f_nom=50, f_min=25, f_max=100, eta_is_max=0.70, pr_opt=2.6, k_pr=0.10,
          k_f=0.10, f_opt=55, clearance=0.03, n_poly=1.12, leak=0.03, eta_motor=0.92, eta_inv=0.97,
          q_loss_frac=0.05)
HP = dict(disp_m3h=27.0, f_nom=50, f_min=25, f_max=100, eta_is_max=0.70, pr_opt=2.6, k_pr=0.10,
          k_f=0.10, f_opt=55, clearance=0.03, n_poly=1.12, leak=0.03, eta_motor=0.92, eta_inv=0.97,
          q_loss_frac=0.05)
CYCLE = dict(
    fluid="Propane", lp=LP, hp=HP, hp_speed_ratio=1.0, pi_factor=1.05,
    m_air_nom=5.4, UA_e=11000.0, fan_min=0.35, W_fan_max=1500.0,
    m_w=1.55, UA_c=9000.0, SH=5.0, SC=3.0, suction_gain=1.0,
    dp_suc=0.06e5, dp_evap=0.12e5, dp_cond=0.10e5, dp_dis=0.08e5, T_dis_max=120.0,
)
