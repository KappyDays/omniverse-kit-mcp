# Robots — Isaac Sim 6.0 Asset Catalog

`$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac`

As of 2026-06-11 S3 LIST actual measurements **50 vendors, 203+ model folders, 228+ top-level USD/USDA**.
Path rule: `$ISAAC/Robots/{Vendor}/{Model}/{file}.usd[a]`.
Drill down to: `asset_list(category="robots", subpath="{Vendor}/{Model}")`.
Scope: Includes only `.usd` directly under the model folder and excludes USD inside `.thumbs/`, `configuration/`, `Props/`, and `Legacy/`.

---

## Classification index by type

| category | Vendor/Model Group |
|---|---|
| **AMR · Mobile** | NVIDIA (Carter · Jetbot · Kaya · Leatherback · NovaCarter) · Clearpath · Addverb Syncro/Trakr · Fraunhofer · AgilexRobotics · Turtlebot · iRobot · Idealworks · IsaacSim DifferentialBase/Forklift/Vehicle |
| **Humanoid/Biped** | 1X · Agibot · Agility · BoosterRobotics · FourierIntelligence (GR-1 series is nested) · Galbot · Ihmcrobotics · RobotEra · SanctuaryAI · Unitree G1/H1 · XHumanoid · XiaoPeng · IsaacSim Humanoid/Humanoid28 |
| **Quadruped walking** | ANYbotics · BostonDynamics · DeepRobotics · Unitree A1/B2/Go1/Go2/aliengo/laikago |
| **Manipulator (arm)** | 85 types of Fanuc · 9 types of UniversalRobots · Kawasaki · Denso · FrankaRobotics · Kinova · Kuka · Flexiv · Mecademic · Techman · Ufactory · OpenArm · RethinkRobotics · RobotStudio · Yahboom · comau |
| **Gripper · Hand** | InspireRobots · Robotiq · Schunk · ShadowRobot · Psyonic · WonikRobotics · Unitree Dex3 |
| **Drone · Aviation** | Bitcraze Crazyflie · NASA Ingenuity · IsaacSim Quadcopter |
| **Education · Simulation** | IsaacSim Ant/Cartpole/SimpleArticulation, etc. · NTNU ARL-Robot-1 |

---

## Top-level USD list by vendor

> ✓ = 2026-06-11 S3 LIST + URL HEAD Verification target. If there are multiple top-level USDs in the same model, separate rows are placed as variants.

| vendor | model | week USD | category |
|---|---|---|---|
| **1X** | Neo | `Neo.usd` ✓ | humanoid |
| **Addverb** | Syncro10 | `Syncro10.usda` ✓ | AMR |
|  | Syncro5 | `Syncro5.usda` ✓ | AMR |
|  | Trakr | `trakr.usd` ✓ | AMR |
| **Agibot** | A2D | `A2D.usd` ✓ | humanoid |
| **AgilexRobotics** | limo | `limo.usd` ✓ | AMR |
| **Agility** | Cassie | `cassie.usd` ✓ | Humanoid/Biped |
|  | Digit | `digit_v4.usd` ✓ | Humanoid/Biped |
| **ANYbotics** | anymal_b | `anymal_b.usd` ✓ | 4 legs |
|  | anymal_c | `anymal_c.usd` ✓ | 4 legs |
|  | anymal_d | `anymal_d.usd` ✓ | 4 legs |
| **Bitcraze** | Crazyflie | `cf2x.usd` ✓ | drone |
| **BoosterRobotics** | BoosterT1 | `T1_locomotion.usd` ✓ | humanoid |
| **BostonDynamics** | spot | `spot.usd` ✓ | 4 legs |
|  | spot | `spot_with_arm.usd` ✓ | 4 legs |
| **Clearpath** | Dingo | `dingo.usd` ✓ | AMR/Mobile+Arm |
|  | Dingo | `dingo_basic.usd` ✓ | AMR/Mobile+Arm |
|  | Jackal | `jackal.usd` ✓ | AMR/Mobile+Arm |
|  | Jackal | `jackal_basic.usd` ✓ | AMR/Mobile+Arm |
|  | RidgebackFranka | `ridgeback_franka.usd` ✓ | AMR/Mobile+Arm |
|  | RidgebackUr | `ridgeback_ur5.usd` ✓ | AMR/Mobile+Arm |
| **comau** | n-220-27 | `n-220-27.usd` ✓ | industrial cancer |
| **DeepRobotics** | Lite3 | `Lite3.usd` ✓ | 4 legs |
|  | M20 | `M20.usd` ✓ | 4 legs |
|  | X30 | `X30.usd` ✓ | 4 legs |
| **Denso** | CobottaPro1300 | `cobotta_pro_1300.usd` ✓ | industrial cancer |
|  | CobottaPro900 | `cobotta_pro_900.usd` ✓ | industrial cancer |
| **Fanuc** | cr_50f_16b | `cr_50f_16b.usd` ✓ | industrial cancer |
|  | crx10ia | `crx10ia.usd` ✓ | industrial cancer |
|  | crx10ia_l | `crx10ia_l.usd` ✓ | industrial cancer |
|  | crx10ia_lp | `crx10ia_lp.usd` ✓ | industrial cancer |
|  | crx20ia_l | `crx20ia_l.usd` ✓ | industrial cancer |
|  | crx30ia | `crx30ia.usd` ✓ | industrial cancer |
|  | crx5ia | `crx5ia.usd` ✓ | industrial cancer |
|  | er4ia | `er4ia.usd` ✓ | industrial cancer |
|  | lrmate10-11a | `lrmate10-11a.usd` ✓ | industrial cancer |
|  | lrmate10-11afc | `lrmate10-11afc.usd` ✓ | industrial cancer |
|  | lrmate14-7d | `lrmate14-7d.usd` ✓ | industrial cancer |
|  | lrmate200id | `lrmate200id.usd` ✓ | industrial cancer |
|  | lrmate200id14l | `lrmate200id14l.usd` ✓ | industrial cancer |
|  | lrmate200id4s | `lrmate200id4s.usd` ✓ | industrial cancer |
|  | lrmate200id7c | `lrmate200id7c.usd` ✓ | industrial cancer |
|  | lrmate200id7l | `lrmate200id7l.usd` ✓ | industrial cancer |
|  | lrmate200id7lc | `lrmate200id7lc.usd` ✓ | industrial cancer |
|  | lrmate200id7we | `lrmate200id7we.usd` ✓ | industrial cancer |
|  | lrmate25-19a | `lrmate25-19a.usd` ✓ | industrial cancer |
|  | lrmate25-19afc | `lrmate25-19afc.usd` ✓ | industrial cancer |
|  | lrmate35-14a | `lrmate35-14a.usd` ✓ | industrial cancer |
|  | m-1000_1000f-33a | `m-1000_1000f-33a.usd` ✓ | industrial cancer |
|  | m-1000_550f-46a | `m-1000_550f-46a.usd` ✓ | industrial cancer |
|  | m-2000_1200f-37a | `m-2000_1200f-37a.usd` ✓ | industrial cancer |
|  | m-2000_1700f-47a | `m-2000_1700f-47a.usd` ✓ | industrial cancer |
|  | m-2000_2300f-37a | `m-2000_2300f-37a.usd` ✓ | industrial cancer |
|  | m-2000_900f-47a | `m-2000_900f-47a.usd` ✓ | industrial cancer |
|  | m10_10-16d | `m10_10-16d.usd` ✓ | industrial cancer |
|  | m10_12-14d | `m10_12-14d.usd` ✓ | industrial cancer |
|  | m10_16-11d | `m10_16-11d.usd` ✓ | industrial cancer |
|  | m10_8-20d | `m10_8-20d.usd` ✓ | industrial cancer |
|  | m20_12-23d | `m20_12-23d.usd` ✓ | industrial cancer |
|  | m20_25-18d | `m20_25-18d.usd` ✓ | industrial cancer |
|  | m20_35-18d | `m20_35-18d.usd` ✓ | industrial cancer |
|  | m710ic_12l | `m710ic_12l.usd` ✓ | industrial cancer |
|  | m710ic_20l | `m710ic_20l.usd` ✓ | industrial cancer |
|  | m710ic_20m | `m710ic_20m.usd` ✓ | industrial cancer |
|  | m710ic_45m | `m710ic_45m.usd` ✓ | industrial cancer |
|  | m710ic_50 | `m710ic_50.usd` ✓ | industrial cancer |
|  | m710ic_50e | `m710ic_50e.usd` ✓ | industrial cancer |
|  | m710ic_50s | `m710ic_50s.usd` ✓ | industrial cancer |
|  | m710ic_70 | `m710ic_70.usd` ✓ | industrial cancer |
|  | m710id_50m | `m710id_50m.usd` ✓ | industrial cancer |
|  | m710id_70 | `m710id_70.usd` ✓ | industrial cancer |
|  | m800_60_20b | `m800_60_20b.usd` ✓ | industrial cancer |
|  | m900ia150p | `m900ia150p.usd` ✓ | industrial cancer |
|  | m900ia200p | `m900ia200p.usd` ✓ | industrial cancer |
|  | m900ib280 | `m900ib280.usd` ✓ | industrial cancer |
|  | m900ib280l | `m900ib280l.usd` ✓ | industrial cancer |
|  | m900ib330l | `m900ib330l.usd` ✓ | industrial cancer |
|  | m900ib360e | `m900ib360e.usd` ✓ | industrial cancer |
|  | m900ib400l | `m900ib400l.usd` ✓ | industrial cancer |
|  | m900ib700 | `m900ib700.usd` ✓ | industrial cancer |
|  | m900ib700e | `m900ib700e.usd` ✓ | industrial cancer |
|  | m950_500f28a | `m950_500f28a.usd` ✓ | industrial cancer |
|  | r1000ia_100f | `r1000ia_100f.usd` ✓ | industrial cancer |
|  | r1000ia_130f | `r1000ia_130f.usd` ✓ | industrial cancer |
|  | r1000ia_80f | `r1000ia_80f.usd` ✓ | industrial cancer |
|  | r2000ic_100p | `r2000ic_100p.usd` ✓ | industrial cancer |
|  | r2000ic_100ph | `r2000ic_100ph.usd` ✓ | industrial cancer |
|  | r2000ic_125l | `r2000ic_125l.usd` ✓ | industrial cancer |
|  | r2000ic_165f | `r2000ic_165f.usd` ✓ | industrial cancer |
|  | r2000ic_165r | `r2000ic_165r.usd` ✓ | industrial cancer |
|  | r2000ic_190s | `r2000ic_190s.usd` ✓ | industrial cancer |
|  | r2000ic_190u | `r2000ic_190u.usd` ✓ | industrial cancer |
|  | r2000ic_210f | `r2000ic_210f.usd` ✓ | industrial cancer |
|  | r2000ic_210l | `r2000ic_210l.usd` ✓ | industrial cancer |
|  | r2000ic_210r | `r2000ic_210r.usd` ✓ | industrial cancer |
|  | r2000ic_210we | `r2000ic_210we.usd` ✓ | industrial cancer |
|  | r2000ic_220u | `r2000ic_220u.usd` ✓ | industrial cancer |
|  | r2000ic_240f | `r2000ic_240f.usd` ✓ | industrial cancer |
|  | r2000ic_270f | `r2000ic_270f.usd` ✓ | industrial cancer |
|  | r2000ic_270r | `r2000ic_270r.usd` ✓ | industrial cancer |
|  | r2000id_100fh | `r2000id_100fh.usd` ✓ | industrial cancer |
|  | r2000id_165fh | `r2000id_165fh.usd` ✓ | industrial cancer |
|  | r2000id_210fh | `r2000id_210fh.usd` ✓ | industrial cancer |
|  | sr12ia | `sr12ia.usd` ✓ | industrial cancer |
|  | sr12iac | `sr12iac.usd` ✓ | industrial cancer |
|  | sr20ia | `sr20ia.usd` ✓ | industrial cancer |
|  | sr3ia | `sr3ia.usd` ✓ | industrial cancer |
|  | sr3iac | `sr3iac.usd` ✓ | industrial cancer |
|  | sr3iau | `sr3iau.usd` ✓ | industrial cancer |
|  | sr6ia | `sr6ia.usd` ✓ | industrial cancer |
|  | sr6iac | `sr6iac.usd` ✓ | industrial cancer |
|  | sr9iar | `sr9iar.usd` ✓ | industrial cancer |
| **Flexiv** | Rizon4 | `flexiv_rizon4.usd` ✓ | cooperative arm |
| **FrankaRobotics** | FactoryFranka | `factory_franka.usd` ✓ | cooperative arm |
|  | FactoryFranka | `factory_franka_instanceable.usd` ✓ | cooperative arm |
|  | FrankaEmika | `panda_instanceable.usd` ✓ | cooperative arm |
|  | FrankaFR3 | `fr3.usd` ✓ | cooperative arm |
|  | FrankaPanda | `franka.usd` ✓ | cooperative arm |
| **Fraunhofer** | Evobot | `evobot.usd` ✓ | AMR |
|  | O3dyn | `o3dyn.usd` ✓ | AMR |
|  | O3dyn | `o3dyn_controller.usd` ✓ | AMR |
|  | O3dyn | `o3dyn_trimmed.usd` ✓ | AMR |
| **Galbot** | galbot_g1 | `galbot_g1.usda` ✓ | humanoid |
| **Idealworks** | iwhub | `iw_hub.usd` ✓ | Industrial AMR |
|  | iwhub | `iw_hub_sensors.usd` ✓ | Industrial AMR |
|  | iwhub | `iw_hub_static.usd` ✓ | Industrial AMR |
| **Ihmcrobotics** | Valkyrie | `valkyrie.usd` ✓ | humanoid |
| **InspireRobots** | Inspire_Hand_RH56DFX_right | `inspire_hand.usda` ✓ | dodge hand |
| **iRobot** | Create3 | `create_3.usd` ✓ | AMR |
| **IsaacSim** | Ant | `ant.usd` ✓ | Training/Simulation |
|  | Ant | `ant_colored.usd` ✓ | Training/Simulation |
|  | Ant | `ant_instanceable.usd` ✓ | Training/Simulation |
|  | BalanceBot | `balance_bot.usd` ✓ | Training/Simulation |
|  | CartDoublePendulum | `cart_double_pendulum.usd` ✓ | Training/Simulation |
|  | Cartpole | `cartpole.usd` ✓ | Training/Simulation |
|  | DifferentialBase | `differential_base.usd` ✓ | Training/Simulation |
|  | ForkliftB | `forklift_b.usd` ✓ | Training/Simulation |
|  | ForkliftB | `forklift_b_sensor.usd` ✓ | Training/Simulation |
|  | ForkliftC | `forklift_c.usd` ✓ | Training/Simulation |
|  | Humanoid | `humanoid.usd` ✓ | Training/Simulation |
|  | Humanoid | `humanoid_instanceable.usd` ✓ | Training/Simulation |
|  | Humanoid28 | `humanoid_28.usd` ✓ | Training/Simulation |
|  | Quadcopter | `quadcopter.usd` ✓ | Training/Simulation |
|  | SimpleArticulation | `articulation_3_joints.usd` ✓ | Training/Simulation |
|  | SimpleArticulation | `revolute_articulation.usd` ✓ | Training/Simulation |
|  | SimpleArticulation | `simple_articulation.usd` ✓ | Training/Simulation |
|  | Vehicle | `basic_vehicle_m.usd` ✓ | Training/Simulation |
| **Kawasaki** | RS007L | `rs007l_onrobot_rg2.usd` ✓ | industrial cancer |
|  | RS007N | `rs007n_onrobot_rg2.usd` ✓ | industrial cancer |
|  | RS013N | `rs013n_onrobot_rg2.usd` ✓ | industrial cancer |
|  | RS025N | `rs025n_onrobot_rg2.usd` ✓ | industrial cancer |
|  | RS080N | `rs080n_onrobot_rg2.usd` ✓ | industrial cancer |
| **Kinova** | Gen3 | `gen3n7_instanceable.usd` ✓ | cooperative arm |
|  | Jaco2/J2N6S300 | `Jaco2/J2N6S300/j2n6s300_instanceable.usd` ✓ | cooperative arm |
|  | Jaco2/J2N7S300 | `Jaco2/J2N7S300/j2n7s300_instanceable.usd` ✓ | cooperative arm |
| **Kuka** | KR210_L150 | `kr210_l150.usd` ✓ | industrial cancer |
| **Mecademic** | meca500 | `meca500.usda` ✓ | small industrial arm |
| **NASA** | Ingenuity | `ingenuity.usd` ✓ | drone |
| **NTNU** | ARL-Robot-1 | `arl_robot_1.usd` ✓ | Research AMR |
| **NVIDIA** | Carter | `carter_v1.usd` ✓ | AMR/Sensor Platform |
|  | Carter | `carter_v1_physx_lidar.usd` ✓ | AMR/Sensor Platform |
|  | Jetbot | `jetbot.usd` ✓ | AMR/Sensor Platform |
|  | Kaya | `kaya.usd` ✓ | AMR/Sensor Platform |
|  | Kaya | `kaya_ogn_gamepad.usd` ✓ | AMR/Sensor Platform |
|  | Leatherback | `leatherback.usd` ✓ | AMR/Sensor Platform |
|  | NovaCarter | `nova_carter.usd` ✓ | AMR/Sensor Platform |
|  | NovaCarterDevKit | `nova_dev_kit_sensors.usd` ✓ | AMR/Sensor Platform |
|  | Robomaker | `aws_robomaker_jetbot.usd` ✓ | AMR/Sensor Platform |
| **OpenArm** | openarm_bimanual | `openarm_bimanual.usd` ✓ | cooperative arm |
|  | openarm_unimanual | `openarm_unimanual.usd` ✓ | cooperative arm |
| **Psyonic** | ability_hand_left_large | `ability_hand_left_large.usd` ✓ | robot hand |
|  | ability_hand_left_small | `ability_hand_left_small.usd` ✓ | robot hand |
|  | ability_hand_right_large | `ability_hand_right_large.usd` ✓ | robot hand |
|  | ability_hand_right_small | `ability_hand_right_small.usd` ✓ | robot hand |
| **RethinkRobotics** | Sawyer | `sawyer_instanceable.usd` ✓ | cooperative arm |
| **RobotEra** | STAR1 | `star1.usd` ✓ | humanoid |
| **Robotiq** | 2F-140 | `2f140_instanceable.usd` ✓ | gripper |
|  | 2F-140 | `Robotiq_2F_140_base.usd` ✓ | gripper |
|  | 2F-140 | `Robotiq_2F_140_config.usd` ✓ | gripper |
|  | 2F-140 | `Robotiq_2F_140_controller.usd` ✓ | gripper |
|  | 2F-140 | `Robotiq_2F_140_physics_edit.usd` ✓ | gripper |
|  | 2F-85 | `Robotiq_2F_85_edit.usd` ✓ | gripper |
|  | Hand-E | `Robotiq_Hand_E_base.usd` ✓ | gripper |
|  | Hand-E | `Robotiq_Hand_E_config.usd` ✓ | gripper |
|  | Hand-E | `Robotiq_Hand_E_edit.usd` ✓ | gripper |
| **RobotStudio** | so100 | `so100.usd` ✓ | small arm |
|  | so101_new_calib | `so101_new_calib.usd` ✓ | small arm |
| **SanctuaryAI** | Phoenix | `phoenix.usd` ✓ | humanoid |
| **Schunk** | egk_25 | `schunk_egk_25.usd` ✓ | gripper |
|  | egu_50 | `schunk_egu_50.usd` ✓ | gripper |
|  | ezu_35 | `schunk_ezu_35.usd` ✓ | gripper |
|  | svh-flat-l | `svh-flat-l_v2.usd` ✓ | gripper |
|  | svh-flat-r | `svh-flat-r_v2.usd` ✓ | gripper |
| **ShadowRobot** | ShadowHand | `shadow_hand.usd` ✓ | robot hand |
|  | ShadowHand | `shadow_hand_instanceable.usd` ✓ | robot hand |
|  | ShadowHand | `shadow_hand_instanceable_newton.usd` ✓ | robot hand |
|  | ShadowHandNoTendons | `shadow_hand.usd` ✓ | robot hand |
|  | ShadowHandNoTendons | `shadow_hand_instanceable.usd` ✓ | robot hand |
| **Techman** | TM12 | `tm12.usd` ✓ | cooperative arm |
| **Turtlebot** | Turtlebot3 | `turtlebot3_burger.usd` ✓ | Education AMR |
| **Ufactory** | lite6 | `lite6.usd` ✓ | Cooperative arm/gripper |
|  | lite6_gripper | `uf_lite_gripper.usd` ✓ | Cooperative arm/gripper |
|  | uf850 | `uf850.usd` ✓ | Cooperative arm/gripper |
|  | xarm6 | `xarm6.usd` ✓ | Cooperative arm/gripper |
|  | xarm7 | `xarm7.usd` ✓ | Cooperative arm/gripper |
|  | xarm_gripper | `xarm_gripper.usd` ✓ | Cooperative arm/gripper |
| **Unitree** | A1 | `a1.usd` ✓ | Four Legs/Humanoid/Hand |
|  | aliengo | `aliengo.usd` ✓ | Four Legs/Humanoid/Hand |
|  | B2 | `b2.usd` ✓ | Four Legs/Humanoid/Hand |
|  | Dex3 | `dex3_1_r.usd` ✓ | Four Legs/Humanoid/Hand |
|  | G1 | `g1.usd` ✓ | Four Legs/Humanoid/Hand |
|  | G1_23dof | `g1.usd` ✓ | Four Legs/Humanoid/Hand |
|  | G1_23dof | `g1_minimal.usd` ✓ | Four Legs/Humanoid/Hand |
|  | Go1 | `go1.usd` ✓ | Four Legs/Humanoid/Hand |
|  | Go1 | `go1_sensor.usd` ✓ | Four Legs/Humanoid/Hand |
|  | Go2 | `go2.usd` ✓ | Four Legs/Humanoid/Hand |
|  | H1 | `h1.usd` ✓ | Four Legs/Humanoid/Hand |
|  | laikago | `laikago.usd` ✓ | Four Legs/Humanoid/Hand |
|  | Z1 | `z1.usd` ✓ | Four Legs/Humanoid/Hand |
| **UniversalRobots** | ur10 | `ur10.usd` ✓ | cooperative arm |
|  | ur10e | `ur10e.usd` ✓ | cooperative arm |
|  | ur16e | `ur16e.usd` ✓ | cooperative arm |
|  | ur20 | `ur20.usd` ✓ | cooperative arm |
|  | ur3 | `ur3.usd` ✓ | cooperative arm |
|  | ur30 | `ur30.usd` ✓ | cooperative arm |
|  | ur3e | `ur3e.usd` ✓ | cooperative arm |
|  | ur5 | `ur5.usd` ✓ | cooperative arm |
|  | ur5e | `ur5e.usd` ✓ | cooperative arm |
| **WonikRobotics** | AllegroHand | `allegro.usd` ✓ | robot hand |
|  | AllegroHand | `allegro_hand.usd` ✓ | robot hand |
|  | AllegroHand | `allegro_hand_instanceable.usd` ✓ | robot hand |
| **XHumanoid** | Tien Kung | `tienkung.usd` ✓ | humanoid |
| **XiaoPeng** | PX5 | `px5.usd` ✓ | humanoid |
|  | PX5 | `px5_without_housing.usd` ✓ | humanoid |
| **Yaskawa** | Motoman Next/NEX10 | `Motoman Next/NEX10/NEX10_C00.usd` ✓ | industrial cancer |
| **Yahboom** | Dofbot | `dofbot.usd` ✓ | education cancer |
