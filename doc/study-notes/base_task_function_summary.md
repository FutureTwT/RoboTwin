# envs/_base_task.py 类与函数说明

本文记录 `envs/_base_task.py` 中的类、函数数量和主要职责。统计基于 Python AST，包含类方法和方法内部定义的局部函数。

## 总体统计

- 类：`1` 个
- `def`：`64` 个
- 类方法：`59` 个
- 方法内部局部函数：`5` 个
- 合计定义数：`65` 个

## 类

| 名称 | 行号 | 作用 |
|---|---:|---|
| `Base_Task` | 36 | RoboTwin 任务环境基类，继承 `gym.Env`，集中管理 SAPIEN 场景、机器人、相机、数据采集、运动规划、抓取、放置和评测执行。 |

## 类方法

### 初始化与场景

📌 备注：支持场景初始化设置，并统一配置光照、材质、相机创建、背景扰动和随机杂物生成。

| 方法 | 行号 | 作用 |
|---|---:|---|
| `__init__` | 38 | 空初始化，真正的环境初始化由 `_init_task_env_` 完成。 |
| `_init_task_env_` | 42 | 初始化任务环境、随机种子、配置项、场景、桌墙、机器人、相机、物体、杂物、稳定性检查和 eval 限制。 |
| `check_stable` | 161 | 推进仿真并检查场景 actor 是否发生过大的姿态变化，用于判断初始场景是否稳定。 |
| `play_once` | 194 | 空接口，留给具体任务子类实现单次任务流程。 |
| `check_success` | 197 | 空接口，留给具体任务子类实现任务成功判定。 |
| `setup_scene` | 200 | 创建 SAPIEN engine、renderer、scene，设置地面、物理材质、光照、viewer 和 ray tracing。 |
| `create_table_and_wall` | 271 | 创建桌子和墙，并根据随机背景配置选择桌面和墙面纹理。 |
| `get_cluttered_table` | 317 | 随机生成桌面杂物，避开任务物体和禁止区域，并记录杂物类型和编号。 |
| `load_robot` | 384 | 创建或重置双臂机器人，初始化 planner、关节，并设置 link mass。 |
| `load_camera` | 402 | 创建并加载相机，推进一次仿真并同步渲染状态。 |
| `_update_render` | 419 | 更新随机灯光、腕部相机位姿和 SAPIEN 渲染状态。 |

### 观测与数据保存

📌 备注：获取 RGB、深度、点云、分割等多模态观测，并支持轨迹存储、轨迹读取和视频保存等。

| 方法 | 行号 | 作用 |
|---|---:|---|
| `get_obs` | 437 | 根据 `data_type` 采集 RGB、第三视角、分割、深度、末端位姿、qpos 和点云等观测。 |
| `save_camera_rgb` | 502 | 保存指定相机的一张 RGB 图像。 |
| `_take_picture` | 508 | 在数据采集模式下保存当前帧观测到 `.cache` 目录中的 pkl 文件。 |
| `save_traj_data` | 527 | 保存左右臂规划轨迹到 `_traj_data/episode*.pkl`。 |
| `load_tran_data` | 535 | 从 `_traj_data/episode*.pkl` 读取已保存的轨迹数据。 |
| `merge_pkl_to_hdf5_video` | 542 | 将缓存 pkl 合并成 episode hdf5 和 mp4 视频。 |
| `remove_data_cache` | 553 | 删除当前 episode 的缓存目录。 |
| `save_camera_images` | 1669 | 保存 head camera 图像到按任务名和生成编号组织的目录。 |

### 指令、路径与环境收尾

📌 备注：无

| 方法 | 行号 | 作用 |
|---|---:|---|
| `set_instruction` | 564 | 设置 eval 使用的自然语言指令。 |
| `get_instruction` | 567 | 读取当前保存的 eval 指令。 |
| `set_path_lst` | 570 | 设置是否重新规划，并写入可复用的左右臂轨迹列表。 |
| `_set_eval_video_ffmpeg` | 575 | 保存 eval 视频写入用的 ffmpeg 进程句柄。 |
| `close_env` | 578 | 关闭环境，可选清理 SAPIEN cache。 |
| `_del_eval_video_ffmpeg` | 585 | 关闭 ffmpeg 标准输入，等待进程结束并删除句柄。 |
| `delay` | 591 | 保持当前夹爪状态，空跑若干仿真步。 |

### 夹爪与禁止区域

📌 备注：支持夹爪设置、夹爪状态判断，并计算禁止区域以辅助随机杂物生成。

| 方法 | 行号 | 作用 |
|---|---:|---|
| `set_gripper` | 606 | 为左、右或双夹爪规划开合轨迹，并在轨迹末尾补一段保持动作。 |
| `add_prohibit_area` | 649 | 根据 actor、pose 或数组估算包围盒，把对应 XY 区域加入桌面禁止放置区。 |
| `is_left_gripper_open` | 688 | 查询左夹爪是否打开。 |
| `is_right_gripper_open` | 691 | 查询右夹爪是否打开。 |
| `is_left_gripper_open_half` | 694 | 查询左夹爪是否半开。 |
| `is_right_gripper_open_half` | 697 | 查询右夹爪是否半开。 |
| `is_left_gripper_close` | 700 | 查询左夹爪是否闭合。 |
| `is_right_gripper_close` | 703 | 查询右夹爪是否闭合。 |
| `together_close_gripper` | 708 | 同步闭合左右夹爪，并调用 dense action 执行。 |
| `together_open_gripper` | 718 | 同步打开左右夹爪，并调用 dense action 执行。 |

### 运动规划与动作封装

📌 备注：支持运动规划、轨迹生成、运动控制和动作封装等。

| 方法 | 行号 | 作用 |
|---|---:|---|
| `left_move_to_pose` | 728 | 左臂规划到目标末端位姿，或在不规划模式下复用已保存轨迹。 |
| `right_move_to_pose` | 761 | 右臂规划到目标末端位姿，或在不规划模式下复用已保存轨迹。 |
| `together_move_to_pose` | 794 | 双臂同步规划并执行到目标位姿，按左右臂轨迹进度交替推进。 |
| `move` | 884 | 执行高层 `Action` 序列，自动分配左右臂动作，并转成底层控制序列。 |
| `move_by_displacement` | 1350 | 根据当前末端位姿生成一个相对偏移后的目标位姿，并封装为移动动作。 |
| `move_to_pose` | 1377 | 将给定目标位姿封装为指定手臂的移动动作，供 `move()` 后续规划执行。 |
| `close_gripper` | 1384 | 将闭合夹爪包装成 action。 |
| `open_gripper` | 1387 | 将打开夹爪包装成 action。 |
| `back_to_origin` | 1390 | 生成回到左臂或右臂初始位姿的 action。 |
| `get_arm_pose` | 1397 | 读取左臂或右臂当前末端位姿。 |

### 接触、抓取与放置

📌 备注：支持接触判断、抓取位姿计算、最优抓取位姿选择和抓取位姿打印等。

| 方法 | 行号 | 作用 |
|---|---:|---|
| `get_gripper_actor_contact_position` | 970 | 获取指定物体与机器人夹爪发生接触的位置，用于判断夹爪是否碰到目标区域。 |
| `check_actors_contact` | 982 | 判断两个 actor 当前是否发生接触。 |
| `get_scene_contact` | 996 | 调试用接口，进入断点并打印场景接触信息。 |
| `choose_best_pose` | 1003 | 从候选 target pose 中选择可规划的抓取位姿。 |
| `_print_all_grasp_pose_of_contact_points` | 1027 | 打印某 actor 所有 contact point 对应的抓取位姿。 |
| `get_grasp_pose` | 1031 | 根据 actor 的 contact point 计算世界系抓取位姿。 |
| `_default_choose_grasp_pose` | 1061 | 默认抓取选择逻辑雏形，目前评分变量基本没有形成完整选择逻辑。 |
| `choose_grasp_pose` | 1080 | 遍历 contact point，选择 pre-grasp pose 和 grasp pose，偏好 top-down 或 side 姿态。 |
| `grasp_actor` | 1167 | 生成抓取动作序列，包括移动到预抓取位姿、接近抓取点和闭合夹爪。 |
| `get_place_pose` | 1220 | 计算让物体本体或 functional point 到达目标 pose 时，机械臂末端应到达的位置。 |
| `place_actor` | 1308 | 生成放置动作序列，包括预放置、放置和可选打开夹爪。 |

### 底层控制与评测执行

| 方法 | 行号 | 作用 |
|---|---:|---|
| `take_dense_action` | 1407 | 执行已经规划好的关节轨迹和夹爪轨迹，并按频率渲染和保存观测。 |
| `take_action` | 1479 | eval 低层接口，接收 qpos 或 ee action，规划或插值后执行，并检查任务是否成功。 |

## 方法内部局部函数

| 局部函数 | 所属方法 | 行号 | 作用 |
|---|---|---:|---|
| `get_sim` | `check_stable` | 166 | 计算两个 pose 的四元数角度差。 |
| `check` | `check_stable` | 171 | 推进仿真若干步，记录 actor pose 并标记不稳定 actor。 |
| `get_actions` | `move` | 894 | 从传入的左右臂 action tuple 中取出指定手臂的动作列表。 |
| `get_grasp_pose` | `choose_grasp_pose` | 1108 | 从 pre-grasp pose 沿局部方向偏移得到真正的 grasp pose。 |
| `check_pose` | `choose_grasp_pose` | 1116 | 检查 pre-pose 和 pose 是否可规划；当前定义后没有被调用。 |

## 代码结构理解

`Base_Task` 可以理解为具体任务脚本的公共执行底座。子类通常负责提供任务物体加载、任务流程和成功判定，而该基类提供以下通用能力：

1. 初始化 SAPIEN 仿真、渲染、桌面、墙、机器人和相机。
2. 统一采集 RGB、深度、分割、点云、qpos 和末端位姿等观测。
3. 将高层抓取、放置、移动、夹爪开合动作转成机器人轨迹。
4. 在数据采集模式下保存 pkl、hdf5、视频和相机图片。
5. 在 eval 模式下执行 qpos 或 ee action，并维护 step limit、视频写入和成功判定。
