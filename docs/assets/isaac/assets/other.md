# IsaacLab · Materials · Samples · Sensors — Isaac Sim 6.0 Asset Catalog

`$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac`

---

## IsaacLab

Root: `$ISAAC/IsaacLab/` — Asset for reinforcement learning/manipulation research.

| folder | use |
|---|---|
| ActuatorNets | Actuator neural network model |
| Arena | RL Arena Environment |
| AutoMate | Automated assembly tasks |
| Contrib | contributed IsaacLab assets |
| Controllers | Controller USD |
| Factory | Factory environment (RL) |
| Materials | Materials exclusive to IsaacLab |
| Mimic | Mimic tasks (Packing, etc.) |
| Objects | RL object |
| Policies | Pre-training policy file |
| PretrainedCheckpoints | checkpoint |
| Robots | IsaacLab exclusive robot |
| TacSL | Tactile Sim-to-Real |
| Tests | test scene |

---

## Materials

Root: `$ISAAC/Materials/`

| folder | use |
|---|---|
| AprilTag | AprilTag Marker Material |
| Base | Basic Material Library |
| Isaac | Isaac Exclusive Materials |
| Textures | texture file |
| vMaterials_2 | NVIDIA vMaterials 2.0 library |

---

## Samples

Root: `$ISAAC/Samples/` — Demo/example scene.

| folder | detail |
|---|---|
| AnimRobot | Animated Robot Example |
| BehaviorTree | Behavior Tree Example |
| BehaviorTreeGen | Behavior Tree generation example |
| Cortex | Cortex example |
| DR | Domain Randomization Example |
| Examples | General example scene |
| Groot | Groot behavior tree example |
| Leonardo | Leonardo example |
| Mujoco_Menagerie | MuJoCo Menagerie import/sample assets |
| NvBlox | NvBlox 3D reconstruction example |
| OmniGraph | OmniGraph example |
| OmniIsaacGymEnvs | OpenAI Gym environment |
| Policies | Policy example |
| ROS2 | ROS2 integration example (`Carter_ROS.usd`, etc.) |
| Replicator | Data generation example |
| Rigging | Rigging Example |
| Scene_Blox | thin blocks |

---

## Sensors

Root: `$ISAAC/Sensors/` — Sensor USD asset (RTX Lidar/Camera configuration file).

| vendor | sensor type |
|---|---|
| HESAI | RTX Lidar (Pandar series) |
| LeopardImaging | camera module |
| Luxonis | OAK/Luxonis camera assets |
| NVIDIA | NVIDIA Sensor |
| Orbbec | RGB-D camera |
| Ouster | RTX Lidar |
| RealSense | Intel RealSense RGB-D Camera |
| SICK | Lidar · Camera |
| Sensing | Camera module (SG2, etc.) |
| Slamtec | 2D Lidar (RPLIDAR) |
| Stereolabs | ZED Stereo Camera |
| Tashan | LightBeam Sensor |
| TexasInstruments | TI radar / sensor assets |
| Velodyne | RTX Lidar |
| ZVISION | RTX Lidar |

> Both `Create > Sensors` menu (prim creation) and USD direct loading are possible.
> `window_menu_trigger` menu_path All: `docs/references/sensor_menu_catalog.md`
