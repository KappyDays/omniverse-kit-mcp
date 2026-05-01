# Robots — Isaac Sim 5.1 Asset Catalog

`$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac`

Isaac Sim 5.1 기준 **44 벤더, 약 100+ 모델**.  
경로 규칙: `$ISAAC/Robots/{Vendor}/{Model}/{model}.usd`  
드릴다운: `asset_list(category="robots", subpath="{Vendor}/{Model}")`

---

## 유형별 분류 인덱스

| 유형 | 벤더/모델 |
|---|---|
| **AMR · 모바일** | NVIDIA (NovaCarter · Carter · Jetbot · Leatherback · Kaya) · Clearpath (Jackal · Dingo · Ridgeback) · Fraunhofer (O3dyn · Evobot) · AgilexRobotics (limo) · Turtlebot (Turtlebot3) · iRobot (Create3) · Idealworks (iwhub) · IsaacSim (DifferentialBase · Vehicle · ForkliftB/C) |
| **휴머노이드** | 1X (Neo) · Agibot (A2D) · Agility (Digit · Cassie) · BoosterRobotics (BoosterT1) · FourierIntelligence (GR-1) · Ihmcrobotics (Valkyrie) · RobotEra (STAR1) · SanctuaryAI (Phoenix) · Unitree (G1 · H1) · XHumanoid (Tien Kung) · XiaoPeng (PX5) · IsaacSim (Humanoid · Humanoid28) |
| **4족보행** | ANYbotics (anymal_b · anymal_c · anymal_d) · BostonDynamics (spot) · Unitree (Go1 · Go2 · A1 · B2 · aliengo · laikago) |
| **매니퓰레이터 (암)** | FrankaRobotics (FrankaPanda · FrankaFR3 · FactoryFranka) · UniversalRobots (ur3~ur30 9종) · Kawasaki (5종) · Kinova (Gen3 · Jaco2) · Kuka (KR210_L150) · Denso (2종) · Fanuc (CRX10IAL) · Festo (FestoCobot) · Flexiv (Rizon4) · Techman (TM12) · Ufactory (xarm6 · xarm7 · uf850 · lite6) · OpenArm (bimanual · unimanual) · RethinkRobotics (Sawyer) · Yaskawa (Motoman Next) · Clearpath (RidgebackFranka · RidgebackUr) |
| **그리퍼 · 핸드** | Robotiq (2F-85 · 2F-140 · Hand-E) · Schunk (egk_25 · egu_50 · ezu_35 · svh-flat-l · svh-flat-r) · ShadowRobot (ShadowHand) · WonikRobotics (AllegroHand) · Unitree (Dex3 · Dex5) |
| **드론 · 항공** | Bitcraze (Crazyflie) · NASA (Ingenuity) · IsaacSim (Quadcopter) |
| **교육 · 시뮬** | IsaacSim (Ant · BalanceBot · Cartpole · CartDoublePendulum · SimpleArticulation) · Turtlebot (Turtlebot3) · Yahboom (Dofbot) · NTNU (ARL-Robot-1) · RobotStudio (so100 · so101) |

---

## 벤더별 전체 목록

> ✓ = 2026-04-23 live 실측. `(추정)` = 폴더 확인됨, 파일명 미실측.

| 벤더 | 모델 | 주 USD | 유형 |
|---|---|---|---|
| **1X** | Neo | `Neo.usd` ✓ | 휴머노이드 |
| **ANYbotics** | anymal_b | `anymal_b.usd` ✓ | 4족 |
| | anymal_c | `anymal_c.usd` ✓ | 4족 |
| | anymal_d | `anymal_d.usd` ✓ | 4족 |
| **Agibot** | A2D | `A2D.usd` ✓ | 휴머노이드 |
| **AgilexRobotics** | limo | `limo.usd` ✓ (64 MB) | AMR |
| **Agility** | Cassie | `cassie.usd` ✓ | 이족보행 |
| | Digit | `digit_v4.usd` ✓ (43 MB) | 휴머노이드 |
| **Bitcraze** | Crazyflie | `cf2x.usd` ✓ | 드론 |
| **BoosterRobotics** | BoosterT1 | `T1_locomotion.usd` ✓ | 휴머노이드 |
| **BostonDynamics** | spot | `spot.usd` ✓ · `spot_with_arm.usd` | 4족 |
| **Clearpath** | Dingo | `dingo.usd` ✓ (17 MB) | AMR |
| | Jackal | `jackal.usd` ✓ | AMR |
| | RidgebackFranka | `ridgeback_franka.usd` ✓ | 모바일+암 |
| | RidgebackUr | `ridgeback_ur5.usd` ✓ | 모바일+암 (UR5) |
| **Denso** | CobottaPro900 | `cobotta_pro_900.usd` ✓ | 협동 암 |
| | CobottaPro1300 | `cobotta_pro_1300.usd` ✓ | 협동 암 |
| **Fanuc** | CRX10IAL | `crx10ial.usd` ✓ | 협동 암 |
| **Festo** | FestoCobot | `festo_cobot.usd` ✓ | 협동 암 |
| **Flexiv** | Rizon4 | `flexiv_rizon4.usd` ✓ | 협동 암 |
| **FourierIntelligence** | GR-1/GR1T1 | `GR-1/GR1T1/GR1_T1.usd` ✓ | 휴머노이드 |
| | GR-1/GR1T2_fourier_hand_6dof | `GR-1/GR1T2_.../...usd` (추정) | 휴머노이드 |
| **FrankaRobotics** | FrankaPanda | `franka.usd` ✓ | 암 |
| | FrankaFR3 | `fr3.usd` ✓ | 암 |
| | FactoryFranka | `factory_franka.usd` (추정) | 암 |
| **Fraunhofer** | Evobot | `evobot.usd` ✓ (43 MB) | AMR |
| | O3dyn | `o3dyn.usd` ✓ | AMR |
| **Idealworks** | iwhub | `iw_hub.usd` ✓ | 산업 AMR |
| **Ihmcrobotics** | Valkyrie | `valkyrie.usd` ✓ | 휴머노이드 |
| **IsaacSim** | Ant | `ant.usd` (추정) | 교육 |
| | BalanceBot | `balance_bot.usd` (추정) | 교육 |
| | CartDoublePendulum | `cart_double_pendulum.usd` (추정) | 교육 |
| | Cartpole | `cartpole.usd` (추정) | 교육 |
| | DifferentialBase | `differential_base.usd` (추정) | AMR 베이스 |
| | ForkliftB/C | `forklift_b/c.usd` (추정) | 지게차 |
| | Humanoid | `humanoid.usd` ✓ | 교육 휴머노이드 |
| | Humanoid28 | `humanoid_28.usd` ✓ | 교육 휴머노이드 28-DOF |
| | Quadcopter | `quadcopter.usd` (추정) | 드론 |
| | SimpleArticulation | `simple_articulation.usd` (추정) | 교육 |
| | Vehicle | `basic_vehicle_m.usd` ✓ | 차량 |
| **Kawasaki** | RS007L | `rs007l_onrobot_rg2.usd` ✓ | 산업 암+RG2 그리퍼 |
| | RS007N | `rs007n_onrobot_rg2.usd` ✓ | 산업 암+RG2 그리퍼 |
| | RS013N | `rs013n_onrobot_rg2.usd` ✓ | 산업 암+RG2 그리퍼 |
| | RS025N | `rs025n_onrobot_rg2.usd` ✓ | 산업 암+RG2 그리퍼 |
| | RS080N | `rs080n_onrobot_rg2.usd` ✓ | 산업 암+RG2 그리퍼 |
| **Kinova** | Gen3 | `gen3n7_instanceable.usd` ✓ | 협동 암 7DOF |
| | Jaco2/J2N6S300 | `Jaco2/J2N6S300/j2n6s300_instanceable.usd` ✓ | 협동 암 |
| | Jaco2/J2N7S300 | `Jaco2/J2N7S300/...usd` (추정) | 협동 암 |
| **Kuka** | KR210_L150 | `kr210_l150.usd` ✓ | 산업 암 |
| **NASA** | Ingenuity | `ingenuity.usd` ✓ | 화성 헬리콥터 |
| **NTNU** | ARL-Robot-1 | `arl_robot_1.usd` ✓ | 연구 |
| **NVIDIA** | Carter | `carter_v1.usd` ✓ | AMR (v1) |
| | Jetbot | `jetbot.usd` ✓ (32 MB) | AMR 소형 |
| | Kaya | `kaya.usd` ✓ | AMR holonomic |
| | Leatherback | `leatherback.usd` ✓ (10 MB) | AMR 4WD |
| | NovaCarter | `nova_carter.usd` ✓ | AMR 대형 |
| | NovaCarterDevKit | `nova_dev_kit_sensors.usd` ✓ | 센서 개발킷 |
| | Robomaker | `aws_robomaker_jetbot.usd` ✓ | AWS Jetbot |
| **OpenArm** | openarm_bimanual | `openarm_bimanual.usd` ✓ | 양팔 암 |
| | openarm_unimanual | `openarm_unimanual.usd` ✓ | 단팔 암 |
| **RethinkRobotics** | Sawyer | `sawyer_instanceable.usd` ✓ | 협동 암 |
| **RobotEra** | STAR1 | `star1.usd` ✓ | 휴머노이드 |
| **RobotStudio** | so100 | `so100.usd` ✓ | 소형 암 |
| | so101_new_calib | `so101_new_calib.usd` ✓ | 소형 암 |
| **Robotiq** | 2F-85 | `Robotiq_2F_85_edit.usd` ✓ | 그리퍼 |
| | 2F-140 | `2f140_instanceable.usd` ✓ | 그리퍼 |
| | Hand-E | `Robotiq_Hand_E_edit.usd` ✓ | 그리퍼 |
| **SanctuaryAI** | Phoenix | `phoenix.usd` ✓ (315 MB!) | 휴머노이드 |
| **Schunk** | egk_25 | `schunk_egk_25.usd` ✓ | 그리퍼 |
| | egu_50 | `schunk_egu_50.usd` ✓ | 그리퍼 |
| | ezu_35 | `schunk_ezu_35.usd` (추정) | 그리퍼 |
| | svh-flat-l | `svh-flat-l_v2.usd` ✓ | 다지 핸드 |
| | svh-flat-r | `svh-flat-r_v2.usd` (추정) | 다지 핸드 |
| **ShadowRobot** | ShadowHand | `shadow_hand.usd` ✓ | 다지 핸드 |
| **Techman** | TM12 | `tm12.usd` ✓ (19 MB) | 협동 암 |
| **Turtlebot** | Turtlebot3 | `turtlebot3_burger.usd` ✓ | 교육 AMR |
| **Ufactory** | lite6 | `lite6.usd` ✓ | 소형 암 |
| | lite6_gripper | `uf_lite_gripper.usd` ✓ | 소형 암+그리퍼 |
| | uf850 | `uf850.usd` ✓ | 암 |
| | xarm6 | `xarm6.usd` ✓ | 암 6DOF |
| | xarm7 | `xarm7.usd` ✓ | 암 7DOF |
| | xarm_gripper | `xarm_gripper.usd` ✓ | 그리퍼 |
| **Unitree** | A1 | `a1.usd` ✓ (36 MB) | 4족 |
| | B2 | `b2.usd` ✓ | 4족 대형 |
| | Dex3 / Dex5 | `dex3/dex5.usd` (추정) | 다지 그리퍼 |
| | G1 | `g1.usd` ✓ | 휴머노이드 |
| | G1_23dof | `g1.usd` ✓ | 휴머노이드 (23-DOF) |
| | Go1 | `go1.usd` ✓ | 4족 |
| | Go2 | `go2.usd` ✓ (28 MB) | 4족 최신 |
| | H1 | `h1.usd` ✓ | 휴머노이드 |
| | Z1 | `z1.usd` (추정) | 암 |
| | aliengo | `aliengo.usd` ✓ | 4족 |
| | laikago | `laikago.usd` (추정) | 4족 구형 |
| **UniversalRobots** | ur3 | `ur3.usd` ✓ | 협동 암 |
| | ur3e / ur5 / ur5e | `ur{N}e?.usd` (패턴 추정) | 협동 암 |
| | ur10 | `ur10.usd` ✓ | 협동 암 |
| | ur10e / ur16e / ur20 / ur30 | `ur{N}e?.usd` (패턴 추정) | 협동 암 |
| **WonikRobotics** | AllegroHand | `allegro_hand.usd` ✓ | 다지 핸드 |
| **XHumanoid** | Tien Kung | `tienkung.usd` ✓ (232 MB!) | 휴머노이드 |
| **XiaoPeng** | PX5 | `px5.usd` ✓ | 휴머노이드 |
| **Yahboom** | Dofbot | `dofbot.usd` ✓ (105 MB) | 교육 암 |
| **Yaskawa** | Motoman Next/NEX10 | `Motoman Next/NEX10/NEX10.usd` ✓ | 산업 암 (3-depth) |
| **iRobot** | Create3 | `create_3.usd` ✓ | AMR 청소 |
