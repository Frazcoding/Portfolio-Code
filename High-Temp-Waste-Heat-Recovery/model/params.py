"""Design parameters for the three HTHP variants (screw compressor, economiser, IHX)."""
SCREW = dict(f_nom=50, f_min=12.5, f_max=50, f_opt=50, eta_is_max=0.76, k_pr=0.08, k_f=0.35, clearance=0.0,
             n_poly=1.1, leak=0.025, eta_motor=0.955, eta_inv=0.975, q_loss_frac=0.02)
COMMON = dict(SH=5.0, SC=3.0, econ_ratio=1.0, econ_dT=5.0, ihx_eps=0.45, dp_suc=0.05e5, dp_evap=0.15e5,
              dp_cond=0.15e5, dp_dis=0.1e5, T0=288.15)
DAIRY_BUTANE = dict(COMMON, fluid="n-Butane", comp=dict(SCREW, disp_m3h=920.0, pr_opt=4.2), sink="water",
                    T_sink_out=95.0, UA_c=75e3, UA_e=95e3, Q_design=650e3, m_src=28.5 * 990 / 3600, T_dis_max=140.0)
DAIRY_R1234ZEZ = dict(DAIRY_BUTANE, fluid="R1234ze(Z)", comp=dict(SCREW, disp_m3h=1000.0, pr_opt=4.2))
STEAM_R1233 = dict(COMMON, fluid="R1233zd(E)", comp=dict(SCREW, disp_m3h=620.0, pr_opt=3.6), sink="steam",
                   T_steam=130.0, UA_c=45e3, UA_e=50e3, Q_design=520e3, m_src=9.5, T_dis_max=168.0, econ_dT=6.0, ihx_eps=0.5)
