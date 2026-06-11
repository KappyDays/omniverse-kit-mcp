# Robots — Isaac Sim 6.0 Asset Catalog

`$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac`

2026-06-11 S3 LIST 실측 기준 **50 벤더, 203+ 모델 폴더, 228+ top-level USD/USDA**.
경로 규칙: `$ISAAC/Robots/{Vendor}/{Model}/{file}.usd[a]`.
드릴다운: `asset_list(category="robots", subpath="{Vendor}/{Model}")`.
범위: 모델 폴더 직하 `.usd`만 수록하고 `.thumbs/`, `configuration/`, `Props/`, `Legacy/` 내부 USD는 제외한다.

---

## 유형별 분류 인덱스

| 유형 | 벤더/모델군 |
|---|---|
| **AMR · 모바일** | NVIDIA (Carter · Jetbot · Kaya · Leatherback · NovaCarter) · Clearpath · Addverb Syncro/Trakr · Fraunhofer · AgilexRobotics · Turtlebot · iRobot · Idealworks · IsaacSim DifferentialBase/Forklift/Vehicle |
| **휴머노이드 · 이족** | 1X · Agibot · Agility · BoosterRobotics · FourierIntelligence(GR-1 계열은 nested) · Galbot · Ihmcrobotics · RobotEra · SanctuaryAI · Unitree G1/H1 · XHumanoid · XiaoPeng · IsaacSim Humanoid/Humanoid28 |
| **4족보행** | ANYbotics · BostonDynamics · DeepRobotics · Unitree A1/B2/Go1/Go2/aliengo/laikago |
| **매니퓰레이터 (암)** | Fanuc 85종 · UniversalRobots 9종 · Kawasaki · Denso · FrankaRobotics · Kinova · Kuka · Flexiv · Mecademic · Techman · Ufactory · OpenArm · RethinkRobotics · RobotStudio · Yahboom · comau |
| **그리퍼 · 핸드** | InspireRobots · Robotiq · Schunk · ShadowRobot · Psyonic · WonikRobotics · Unitree Dex3 |
| **드론 · 항공** | Bitcraze Crazyflie · NASA Ingenuity · IsaacSim Quadcopter |
| **교육 · 시뮬** | IsaacSim Ant/Cartpole/SimpleArticulation 등 · NTNU ARL-Robot-1 |

---

## 벤더별 top-level USD 목록

> ✓ = 2026-06-11 S3 LIST + URL HEAD 검증 대상. 동일 모델에 여러 top-level USD가 있으면 variant로 별도 행을 둔다.

| 벤더 | 모델 | 주 USD | 유형 |
|---|---|---|---|
| **1X** | Neo | `Neo.usd` ✓ | 휴머노이드 |
| **Addverb** | Syncro10 | `Syncro10.usda` ✓ | AMR |
|  | Syncro5 | `Syncro5.usda` ✓ | AMR |
|  | Trakr | `trakr.usd` ✓ | AMR |
| **Agibot** | A2D | `A2D.usd` ✓ | 휴머노이드 |
| **AgilexRobotics** | limo | `limo.usd` ✓ | AMR |
| **Agility** | Cassie | `cassie.usd` ✓ | 휴머노이드/이족 |
|  | Digit | `digit_v4.usd` ✓ | 휴머노이드/이족 |
| **ANYbotics** | anymal_b | `anymal_b.usd` ✓ | 4족 |
|  | anymal_c | `anymal_c.usd` ✓ | 4족 |
|  | anymal_d | `anymal_d.usd` ✓ | 4족 |
| **Bitcraze** | Crazyflie | `cf2x.usd` ✓ | 드론 |
| **BoosterRobotics** | BoosterT1 | `T1_locomotion.usd` ✓ | 휴머노이드 |
| **BostonDynamics** | spot | `spot.usd` ✓ | 4족 |
|  | spot | `spot_with_arm.usd` ✓ | 4족 |
| **Clearpath** | Dingo | `dingo.usd` ✓ | AMR/모바일+암 |
|  | Dingo | `dingo_basic.usd` ✓ | AMR/모바일+암 |
|  | Jackal | `jackal.usd` ✓ | AMR/모바일+암 |
|  | Jackal | `jackal_basic.usd` ✓ | AMR/모바일+암 |
|  | RidgebackFranka | `ridgeback_franka.usd` ✓ | AMR/모바일+암 |
|  | RidgebackUr | `ridgeback_ur5.usd` ✓ | AMR/모바일+암 |
| **comau** | n-220-27 | `n-220-27.usd` ✓ | 산업 암 |
| **DeepRobotics** | Lite3 | `Lite3.usd` ✓ | 4족 |
|  | M20 | `M20.usd` ✓ | 4족 |
|  | X30 | `X30.usd` ✓ | 4족 |
| **Denso** | CobottaPro1300 | `cobotta_pro_1300.usd` ✓ | 산업 암 |
|  | CobottaPro900 | `cobotta_pro_900.usd` ✓ | 산업 암 |
| **Fanuc** | cr_50f_16b | `cr_50f_16b.usd` ✓ | 산업 암 |
|  | crx10ia | `crx10ia.usd` ✓ | 산업 암 |
|  | crx10ia_l | `crx10ia_l.usd` ✓ | 산업 암 |
|  | crx10ia_lp | `crx10ia_lp.usd` ✓ | 산업 암 |
|  | crx20ia_l | `crx20ia_l.usd` ✓ | 산업 암 |
|  | crx30ia | `crx30ia.usd` ✓ | 산업 암 |
|  | crx5ia | `crx5ia.usd` ✓ | 산업 암 |
|  | er4ia | `er4ia.usd` ✓ | 산업 암 |
|  | lrmate10-11a | `lrmate10-11a.usd` ✓ | 산업 암 |
|  | lrmate10-11afc | `lrmate10-11afc.usd` ✓ | 산업 암 |
|  | lrmate14-7d | `lrmate14-7d.usd` ✓ | 산업 암 |
|  | lrmate200id | `lrmate200id.usd` ✓ | 산업 암 |
|  | lrmate200id14l | `lrmate200id14l.usd` ✓ | 산업 암 |
|  | lrmate200id4s | `lrmate200id4s.usd` ✓ | 산업 암 |
|  | lrmate200id7c | `lrmate200id7c.usd` ✓ | 산업 암 |
|  | lrmate200id7l | `lrmate200id7l.usd` ✓ | 산업 암 |
|  | lrmate200id7lc | `lrmate200id7lc.usd` ✓ | 산업 암 |
|  | lrmate200id7we | `lrmate200id7we.usd` ✓ | 산업 암 |
|  | lrmate25-19a | `lrmate25-19a.usd` ✓ | 산업 암 |
|  | lrmate25-19afc | `lrmate25-19afc.usd` ✓ | 산업 암 |
|  | lrmate35-14a | `lrmate35-14a.usd` ✓ | 산업 암 |
|  | m-1000_1000f-33a | `m-1000_1000f-33a.usd` ✓ | 산업 암 |
|  | m-1000_550f-46a | `m-1000_550f-46a.usd` ✓ | 산업 암 |
|  | m-2000_1200f-37a | `m-2000_1200f-37a.usd` ✓ | 산업 암 |
|  | m-2000_1700f-47a | `m-2000_1700f-47a.usd` ✓ | 산업 암 |
|  | m-2000_2300f-37a | `m-2000_2300f-37a.usd` ✓ | 산업 암 |
|  | m-2000_900f-47a | `m-2000_900f-47a.usd` ✓ | 산업 암 |
|  | m10_10-16d | `m10_10-16d.usd` ✓ | 산업 암 |
|  | m10_12-14d | `m10_12-14d.usd` ✓ | 산업 암 |
|  | m10_16-11d | `m10_16-11d.usd` ✓ | 산업 암 |
|  | m10_8-20d | `m10_8-20d.usd` ✓ | 산업 암 |
|  | m20_12-23d | `m20_12-23d.usd` ✓ | 산업 암 |
|  | m20_25-18d | `m20_25-18d.usd` ✓ | 산업 암 |
|  | m20_35-18d | `m20_35-18d.usd` ✓ | 산업 암 |
|  | m710ic_12l | `m710ic_12l.usd` ✓ | 산업 암 |
|  | m710ic_20l | `m710ic_20l.usd` ✓ | 산업 암 |
|  | m710ic_20m | `m710ic_20m.usd` ✓ | 산업 암 |
|  | m710ic_45m | `m710ic_45m.usd` ✓ | 산업 암 |
|  | m710ic_50 | `m710ic_50.usd` ✓ | 산업 암 |
|  | m710ic_50e | `m710ic_50e.usd` ✓ | 산업 암 |
|  | m710ic_50s | `m710ic_50s.usd` ✓ | 산업 암 |
|  | m710ic_70 | `m710ic_70.usd` ✓ | 산업 암 |
|  | m710id_50m | `m710id_50m.usd` ✓ | 산업 암 |
|  | m710id_70 | `m710id_70.usd` ✓ | 산업 암 |
|  | m800_60_20b | `m800_60_20b.usd` ✓ | 산업 암 |
|  | m900ia150p | `m900ia150p.usd` ✓ | 산업 암 |
|  | m900ia200p | `m900ia200p.usd` ✓ | 산업 암 |
|  | m900ib280 | `m900ib280.usd` ✓ | 산업 암 |
|  | m900ib280l | `m900ib280l.usd` ✓ | 산업 암 |
|  | m900ib330l | `m900ib330l.usd` ✓ | 산업 암 |
|  | m900ib360e | `m900ib360e.usd` ✓ | 산업 암 |
|  | m900ib400l | `m900ib400l.usd` ✓ | 산업 암 |
|  | m900ib700 | `m900ib700.usd` ✓ | 산업 암 |
|  | m900ib700e | `m900ib700e.usd` ✓ | 산업 암 |
|  | m950_500f28a | `m950_500f28a.usd` ✓ | 산업 암 |
|  | r1000ia_100f | `r1000ia_100f.usd` ✓ | 산업 암 |
|  | r1000ia_130f | `r1000ia_130f.usd` ✓ | 산업 암 |
|  | r1000ia_80f | `r1000ia_80f.usd` ✓ | 산업 암 |
|  | r2000ic_100p | `r2000ic_100p.usd` ✓ | 산업 암 |
|  | r2000ic_100ph | `r2000ic_100ph.usd` ✓ | 산업 암 |
|  | r2000ic_125l | `r2000ic_125l.usd` ✓ | 산업 암 |
|  | r2000ic_165f | `r2000ic_165f.usd` ✓ | 산업 암 |
|  | r2000ic_165r | `r2000ic_165r.usd` ✓ | 산업 암 |
|  | r2000ic_190s | `r2000ic_190s.usd` ✓ | 산업 암 |
|  | r2000ic_190u | `r2000ic_190u.usd` ✓ | 산업 암 |
|  | r2000ic_210f | `r2000ic_210f.usd` ✓ | 산업 암 |
|  | r2000ic_210l | `r2000ic_210l.usd` ✓ | 산업 암 |
|  | r2000ic_210r | `r2000ic_210r.usd` ✓ | 산업 암 |
|  | r2000ic_210we | `r2000ic_210we.usd` ✓ | 산업 암 |
|  | r2000ic_220u | `r2000ic_220u.usd` ✓ | 산업 암 |
|  | r2000ic_240f | `r2000ic_240f.usd` ✓ | 산업 암 |
|  | r2000ic_270f | `r2000ic_270f.usd` ✓ | 산업 암 |
|  | r2000ic_270r | `r2000ic_270r.usd` ✓ | 산업 암 |
|  | r2000id_100fh | `r2000id_100fh.usd` ✓ | 산업 암 |
|  | r2000id_165fh | `r2000id_165fh.usd` ✓ | 산업 암 |
|  | r2000id_210fh | `r2000id_210fh.usd` ✓ | 산업 암 |
|  | sr12ia | `sr12ia.usd` ✓ | 산업 암 |
|  | sr12iac | `sr12iac.usd` ✓ | 산업 암 |
|  | sr20ia | `sr20ia.usd` ✓ | 산업 암 |
|  | sr3ia | `sr3ia.usd` ✓ | 산업 암 |
|  | sr3iac | `sr3iac.usd` ✓ | 산업 암 |
|  | sr3iau | `sr3iau.usd` ✓ | 산업 암 |
|  | sr6ia | `sr6ia.usd` ✓ | 산업 암 |
|  | sr6iac | `sr6iac.usd` ✓ | 산업 암 |
|  | sr9iar | `sr9iar.usd` ✓ | 산업 암 |
| **Flexiv** | Rizon4 | `flexiv_rizon4.usd` ✓ | 협동 암 |
| **FrankaRobotics** | FactoryFranka | `factory_franka.usd` ✓ | 협동 암 |
|  | FactoryFranka | `factory_franka_instanceable.usd` ✓ | 협동 암 |
|  | FrankaEmika | `panda_instanceable.usd` ✓ | 협동 암 |
|  | FrankaFR3 | `fr3.usd` ✓ | 협동 암 |
|  | FrankaPanda | `franka.usd` ✓ | 협동 암 |
| **Fraunhofer** | Evobot | `evobot.usd` ✓ | AMR |
|  | O3dyn | `o3dyn.usd` ✓ | AMR |
|  | O3dyn | `o3dyn_controller.usd` ✓ | AMR |
|  | O3dyn | `o3dyn_trimmed.usd` ✓ | AMR |
| **Galbot** | galbot_g1 | `galbot_g1.usda` ✓ | 휴머노이드 |
| **Idealworks** | iwhub | `iw_hub.usd` ✓ | 산업 AMR |
|  | iwhub | `iw_hub_sensors.usd` ✓ | 산업 AMR |
|  | iwhub | `iw_hub_static.usd` ✓ | 산업 AMR |
| **Ihmcrobotics** | Valkyrie | `valkyrie.usd` ✓ | 휴머노이드 |
| **InspireRobots** | Inspire_Hand_RH56DFX_right | `inspire_hand.usda` ✓ | 다지 핸드 |
| **iRobot** | Create3 | `create_3.usd` ✓ | AMR |
| **IsaacSim** | Ant | `ant.usd` ✓ | 교육/시뮬 |
|  | Ant | `ant_colored.usd` ✓ | 교육/시뮬 |
|  | Ant | `ant_instanceable.usd` ✓ | 교육/시뮬 |
|  | BalanceBot | `balance_bot.usd` ✓ | 교육/시뮬 |
|  | CartDoublePendulum | `cart_double_pendulum.usd` ✓ | 교육/시뮬 |
|  | Cartpole | `cartpole.usd` ✓ | 교육/시뮬 |
|  | DifferentialBase | `differential_base.usd` ✓ | 교육/시뮬 |
|  | ForkliftB | `forklift_b.usd` ✓ | 교육/시뮬 |
|  | ForkliftB | `forklift_b_sensor.usd` ✓ | 교육/시뮬 |
|  | ForkliftC | `forklift_c.usd` ✓ | 교육/시뮬 |
|  | Humanoid | `humanoid.usd` ✓ | 교육/시뮬 |
|  | Humanoid | `humanoid_instanceable.usd` ✓ | 교육/시뮬 |
|  | Humanoid28 | `humanoid_28.usd` ✓ | 교육/시뮬 |
|  | Quadcopter | `quadcopter.usd` ✓ | 교육/시뮬 |
|  | SimpleArticulation | `articulation_3_joints.usd` ✓ | 교육/시뮬 |
|  | SimpleArticulation | `revolute_articulation.usd` ✓ | 교육/시뮬 |
|  | SimpleArticulation | `simple_articulation.usd` ✓ | 교육/시뮬 |
|  | Vehicle | `basic_vehicle_m.usd` ✓ | 교육/시뮬 |
| **Kawasaki** | RS007L | `rs007l_onrobot_rg2.usd` ✓ | 산업 암 |
|  | RS007N | `rs007n_onrobot_rg2.usd` ✓ | 산업 암 |
|  | RS013N | `rs013n_onrobot_rg2.usd` ✓ | 산업 암 |
|  | RS025N | `rs025n_onrobot_rg2.usd` ✓ | 산업 암 |
|  | RS080N | `rs080n_onrobot_rg2.usd` ✓ | 산업 암 |
| **Kinova** | Gen3 | `gen3n7_instanceable.usd` ✓ | 협동 암 |
| **Kuka** | KR210_L150 | `kr210_l150.usd` ✓ | 산업 암 |
| **Mecademic** | meca500 | `meca500.usda` ✓ | 소형 산업 암 |
| **NASA** | Ingenuity | `ingenuity.usd` ✓ | 드론 |
| **NTNU** | ARL-Robot-1 | `arl_robot_1.usd` ✓ | 연구 AMR |
| **NVIDIA** | Carter | `carter_v1.usd` ✓ | AMR/센서 플랫폼 |
|  | Carter | `carter_v1_physx_lidar.usd` ✓ | AMR/센서 플랫폼 |
|  | Jetbot | `jetbot.usd` ✓ | AMR/센서 플랫폼 |
|  | Kaya | `kaya.usd` ✓ | AMR/센서 플랫폼 |
|  | Kaya | `kaya_ogn_gamepad.usd` ✓ | AMR/센서 플랫폼 |
|  | Leatherback | `leatherback.usd` ✓ | AMR/센서 플랫폼 |
|  | NovaCarter | `nova_carter.usd` ✓ | AMR/센서 플랫폼 |
|  | NovaCarterDevKit | `nova_dev_kit_sensors.usd` ✓ | AMR/센서 플랫폼 |
|  | Robomaker | `aws_robomaker_jetbot.usd` ✓ | AMR/센서 플랫폼 |
| **OpenArm** | openarm_bimanual | `openarm_bimanual.usd` ✓ | 협동 암 |
|  | openarm_unimanual | `openarm_unimanual.usd` ✓ | 협동 암 |
| **Psyonic** | ability_hand_left_large | `ability_hand_left_large.usd` ✓ | 로봇 핸드 |
|  | ability_hand_left_small | `ability_hand_left_small.usd` ✓ | 로봇 핸드 |
|  | ability_hand_right_large | `ability_hand_right_large.usd` ✓ | 로봇 핸드 |
|  | ability_hand_right_small | `ability_hand_right_small.usd` ✓ | 로봇 핸드 |
| **RethinkRobotics** | Sawyer | `sawyer_instanceable.usd` ✓ | 협동 암 |
| **RobotEra** | STAR1 | `star1.usd` ✓ | 휴머노이드 |
| **Robotiq** | 2F-140 | `2f140_instanceable.usd` ✓ | 그리퍼 |
|  | 2F-140 | `Robotiq_2F_140_base.usd` ✓ | 그리퍼 |
|  | 2F-140 | `Robotiq_2F_140_config.usd` ✓ | 그리퍼 |
|  | 2F-140 | `Robotiq_2F_140_controller.usd` ✓ | 그리퍼 |
|  | 2F-140 | `Robotiq_2F_140_physics_edit.usd` ✓ | 그리퍼 |
|  | 2F-85 | `Robotiq_2F_85_edit.usd` ✓ | 그리퍼 |
|  | Hand-E | `Robotiq_Hand_E_base.usd` ✓ | 그리퍼 |
|  | Hand-E | `Robotiq_Hand_E_config.usd` ✓ | 그리퍼 |
|  | Hand-E | `Robotiq_Hand_E_edit.usd` ✓ | 그리퍼 |
| **RobotStudio** | so100 | `so100.usd` ✓ | 소형 암 |
|  | so101_new_calib | `so101_new_calib.usd` ✓ | 소형 암 |
| **SanctuaryAI** | Phoenix | `phoenix.usd` ✓ | 휴머노이드 |
| **Schunk** | egk_25 | `schunk_egk_25.usd` ✓ | 그리퍼 |
|  | egu_50 | `schunk_egu_50.usd` ✓ | 그리퍼 |
|  | ezu_35 | `schunk_ezu_35.usd` ✓ | 그리퍼 |
|  | svh-flat-l | `svh-flat-l_v2.usd` ✓ | 그리퍼 |
|  | svh-flat-r | `svh-flat-r_v2.usd` ✓ | 그리퍼 |
| **ShadowRobot** | ShadowHand | `shadow_hand.usd` ✓ | 로봇 핸드 |
|  | ShadowHand | `shadow_hand_instanceable.usd` ✓ | 로봇 핸드 |
|  | ShadowHand | `shadow_hand_instanceable_newton.usd` ✓ | 로봇 핸드 |
|  | ShadowHandNoTendons | `shadow_hand.usd` ✓ | 로봇 핸드 |
|  | ShadowHandNoTendons | `shadow_hand_instanceable.usd` ✓ | 로봇 핸드 |
| **Techman** | TM12 | `tm12.usd` ✓ | 협동 암 |
| **Turtlebot** | Turtlebot3 | `turtlebot3_burger.usd` ✓ | 교육 AMR |
| **Ufactory** | lite6 | `lite6.usd` ✓ | 협동 암/그리퍼 |
|  | lite6_gripper | `uf_lite_gripper.usd` ✓ | 협동 암/그리퍼 |
|  | uf850 | `uf850.usd` ✓ | 협동 암/그리퍼 |
|  | xarm6 | `xarm6.usd` ✓ | 협동 암/그리퍼 |
|  | xarm7 | `xarm7.usd` ✓ | 협동 암/그리퍼 |
|  | xarm_gripper | `xarm_gripper.usd` ✓ | 협동 암/그리퍼 |
| **Unitree** | A1 | `a1.usd` ✓ | 4족/휴머노이드/핸드 |
|  | aliengo | `aliengo.usd` ✓ | 4족/휴머노이드/핸드 |
|  | B2 | `b2.usd` ✓ | 4족/휴머노이드/핸드 |
|  | Dex3 | `dex3_1_r.usd` ✓ | 4족/휴머노이드/핸드 |
|  | G1 | `g1.usd` ✓ | 4족/휴머노이드/핸드 |
|  | G1_23dof | `g1.usd` ✓ | 4족/휴머노이드/핸드 |
|  | G1_23dof | `g1_minimal.usd` ✓ | 4족/휴머노이드/핸드 |
|  | Go1 | `go1.usd` ✓ | 4족/휴머노이드/핸드 |
|  | Go1 | `go1_sensor.usd` ✓ | 4족/휴머노이드/핸드 |
|  | Go2 | `go2.usd` ✓ | 4족/휴머노이드/핸드 |
|  | H1 | `h1.usd` ✓ | 4족/휴머노이드/핸드 |
|  | laikago | `laikago.usd` ✓ | 4족/휴머노이드/핸드 |
|  | Z1 | `z1.usd` ✓ | 4족/휴머노이드/핸드 |
| **UniversalRobots** | ur10 | `ur10.usd` ✓ | 협동 암 |
|  | ur10e | `ur10e.usd` ✓ | 협동 암 |
|  | ur16e | `ur16e.usd` ✓ | 협동 암 |
|  | ur20 | `ur20.usd` ✓ | 협동 암 |
|  | ur3 | `ur3.usd` ✓ | 협동 암 |
|  | ur30 | `ur30.usd` ✓ | 협동 암 |
|  | ur3e | `ur3e.usd` ✓ | 협동 암 |
|  | ur5 | `ur5.usd` ✓ | 협동 암 |
|  | ur5e | `ur5e.usd` ✓ | 협동 암 |
| **WonikRobotics** | AllegroHand | `allegro.usd` ✓ | 로봇 핸드 |
|  | AllegroHand | `allegro_hand.usd` ✓ | 로봇 핸드 |
|  | AllegroHand | `allegro_hand_instanceable.usd` ✓ | 로봇 핸드 |
| **XHumanoid** | Tien Kung | `tienkung.usd` ✓ | 휴머노이드 |
| **XiaoPeng** | PX5 | `px5.usd` ✓ | 휴머노이드 |
|  | PX5 | `px5_without_housing.usd` ✓ | 휴머노이드 |
| **Yaskawa** | Motoman Next/NEX10 | `Motoman Next/NEX10/NEX10_C00.usd` ✓ | 산업 암 |
| **Yahboom** | Dofbot | `dofbot.usd` ✓ | 교육 암 |
