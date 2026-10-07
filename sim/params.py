"""Two-stage R717 heat pump for the 400 m2 glasshouse (open reciprocating compressors, flash economiser)."""
RECIP = dict(f_nom=50, f_min=25, f_max=60, eta_is_max=0.76, pr_opt=3.0, k_pr=0.07, k_f=0.05, f_opt=45,
             clearance=0.045, n_poly=1.25, leak=0.02, eta_motor=0.94, eta_inv=0.97, q_loss_frac=0.10)
BASE = dict(fluid="Ammonia", lp=dict(RECIP, disp_m3h=118.0), hp=dict(RECIP, disp_m3h=46.0), hp_speed_ratio=1.0,
            pi_factor=1.05, intercooler="open", m_w=2.4, UA_c=14000.0, SH=5.0, SC=3.0, suction_gain=1.0,
            dp_suc=0.05e5, dp_evap=0.08e5, dp_cond=0.08e5, dp_dis=0.08e5, T_dis_max=150.0, fan_min=0.35)
AIR = dict(BASE, source="air", m_air_nom=9.0, UA_e=18000.0, W_fan_max=2600.0)
GROUND = dict(BASE, source="liquid", m_src=4.2, cp_src=3800.0, UA_e=16000.0, W_src_pump=1600.0, T0=283.15, W_fan_max=0.0)
WATER = dict(BASE, source="liquid", m_src=5.0, cp_src=4190.0, UA_e=18000.0, W_src_pump=2600.0, T0=283.15, W_fan_max=0.0)
