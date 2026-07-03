# script/collect_data.py 主流程说明

本文记录 `script/collect_data.py` 的主要逻辑。这个脚本是 RoboTwin 数据采集入口，核心流程是：先搜索可成功执行任务的随机种子并保存轨迹，再复用这些轨迹正式采集观测数据。

## 一、入口作用

常见运行方式：

```bash
python script/collect_data.py adjust_bottle demo_clean
```

两个参数含义：

| 参数 | 示例 | 作用 |
|---|---|---|
| `task_name` | `adjust_bottle` | 指定任务名，对应 `envs/adjust_bottle.py` 中的任务类。 |
| `task_config` | `demo_clean` | 指定配置名，对应 `task_config/demo_clean.yml`。 |

脚本入口会先运行 `Sapien_TEST()` 检查 SAPIEN 渲染环境，然后设置 multiprocessing 的启动方式为 `spawn`，最后调用 `main(task_name, task_config)`。

## 二、任务与配置加载

### 1. 动态加载任务环境

`class_decorator(task_name)` 会根据任务名动态导入环境模块：

```python
envs_module = importlib.import_module(f"envs.{task_name}")
env_class = getattr(envs_module, task_name)
env_instance = env_class()
```

例如 `task_name=adjust_bottle` 时，会加载：

```text
envs/adjust_bottle.py
```

并实例化其中同名任务类 `adjust_bottle`。

### 2. 读取任务配置

`main()` 会读取：

```text
task_config/<task_config>.yml
```

例如：

```text
task_config/demo_clean.yml
```

配置中主要包含：

| 配置类别 | 作用 |
|---|---|
| episode 设置 | 控制采集多少条 episode、是否使用已有 seed。 |
| domain randomization | 控制随机背景、随机光照、桌面杂物、桌面高度等。 |
| camera | 控制头部相机、腕部相机类型及是否采集。 |
| data_type | 控制是否保存 RGB、深度、点云、分割、末端位姿、关节状态等。 |
| save 设置 | 控制保存路径、缓存清理频率、是否保存 eval 视频等。 |

### 3. 加载机器人 embodiment

脚本会读取：

```text
CONFIGS_PATH/_embodiment_config.yml
```

根据配置里的 `embodiment` 找到机器人文件路径，再读取对应机器人的 `config.yml`。

如果配置是：

```yaml
embodiment: [aloha-agilex]
```

表示左右臂都使用同一种机器人配置：

```python
args["left_robot_file"] = ...
args["right_robot_file"] = ...
args["dual_arm_embodied"] = True
```

如果 `embodiment` 中有三个参数，则表示左右臂使用不同 embodiment，并通过第三个参数设置左右机器人间距。

## 三、第一阶段：搜索成功 seed 并保存轨迹

当配置中：

```yaml
use_seed: false
```

脚本会进入 seed 搜索阶段：

```python
args["need_plan"] = True
```

这一阶段会从 `epid = 0` 开始不断尝试不同随机种子：

```python
TASK_ENV.setup_demo(now_ep_num=suc_num, seed=epid, **args)
TASK_ENV.play_once()
```

然后判断任务是否成功：

```python
TASK_ENV.plan_success and TASK_ENV.check_success()
```

如果成功，会做三件事：

| 操作 | 作用 |
|---|---|
| 记录 seed | 把当前 `epid` 写入 `seed.txt`。 |
| 保存轨迹 | 调用 `save_traj_data(suc_num)` 保存左右臂规划轨迹。 |
| 成功数加一 | `suc_num += 1`，直到达到 `episode_num`。 |

如果失败，则换下一个 seed 继续尝试。

这一阶段的重点不是正式保存 RGB/深度等数据，而是找到“能成功完成任务的随机场景”，并保存对应的运动轨迹。

## 四、第二阶段：复用轨迹并正式采集数据

如果配置中：

```yaml
collect_data: true
```

脚本会进入正式数据采集阶段：

```python
args["need_plan"] = False
args["render_freq"] = 0
args["save_data"] = True
```

这几个设置的含义是：

| 参数 | 含义 |
|---|---|
| `need_plan = False` | 不重新运动规划，复用第一阶段保存的轨迹。 |
| `render_freq = 0` | 关闭 SAPIEN Viewer，避免远程采集时 GUI 拖慢速度。 |
| `save_data = True` | 开启观测数据保存。 |

每个 episode 会按以下流程执行：

```python
TASK_ENV.setup_demo(now_ep_num=episode_idx, seed=seed_list[episode_idx], **args)
traj_data = TASK_ENV.load_tran_data(episode_idx)
args["left_joint_path"] = traj_data["left_joint_path"]
args["right_joint_path"] = traj_data["right_joint_path"]
TASK_ENV.set_path_lst(args)
info = TASK_ENV.play_once()
```

也就是说，第二阶段会：

1. 用第一阶段筛选出的 seed 重新初始化同一个场景。
2. 读取第一阶段保存的左右臂轨迹。
3. 调用 `set_path_lst()` 写入可复用轨迹。
4. 执行 `play_once()`，但此时不再规划，而是复用轨迹。
5. 保存 RGB、qpos、endpose 等配置中打开的数据。

## 五、数据保存位置

最终保存路径由配置中的 `save_path`、任务名和配置名共同决定：

```text
<save_path>/<task_name>/<task_config>/
```

例如：

```text
data/adjust_bottle/demo_clean/
```

常见输出包括：

| 文件或目录 | 作用 |
|---|---|
| `seed.txt` | 保存成功 episode 对应的随机种子。 |
| `_traj_data/episode*.pkl` | 保存第一阶段规划得到的左右臂轨迹。 |
| `data/episode*.hdf5` | 保存正式采集到的 episode 数据。 |
| `scene_info.json` | 保存每个 episode 的场景信息，用于后续生成语言指令。 |
| `instructions/episode*.json` | 保存生成后的自然语言指令。 |

正式采集时，环境会先把每一帧观测临时保存到 `.cache`，然后调用：

```python
TASK_ENV.merge_pkl_to_hdf5_video()
TASK_ENV.remove_data_cache()
```

把缓存合并成 hdf5 和视频文件，再清理临时缓存。

## 六、语言指令生成

数据采集完成后，脚本会运行：

```python
cd description && bash gen_episode_instructions.sh <task_name> <task_config> <language_num>
```

这里的 `language_num` 来自任务配置，例如：

```yaml
language_num: 100
```

它表示每个 episode 最多生成多少条自然语言指令。生成逻辑主要基于：

| 来源 | 作用 |
|---|---|
| `scene_info.json` | 提供每个 episode 的物体、机械臂等场景参数。 |
| `description/task_instruction/<task_name>.json` | 提供任务语言模板。 |
| `language_num` | 控制生成指令数量上限。 |

## 七、整体流程图

```text
命令行参数
  |
  v
读取 task_config/*.yml
  |
  v
加载任务类 envs/<task_name>.py
  |
  v
加载机器人 embodiment 配置
  |
  v
第一阶段：need_plan = True
  |
  +--> setup_demo(seed)
  +--> play_once()
  +--> check_success()
  +--> 成功则保存 seed.txt 和 _traj_data/*.pkl
  |
  v
第二阶段：need_plan = False, save_data = True
  |
  +--> 用成功 seed 重建场景
  +--> 读取 _traj_data/*.pkl
  +--> set_path_lst() 复用轨迹
  +--> play_once() 执行动作并保存观测
  +--> 合并为 data/episode*.hdf5
  |
  v
生成 instructions/episode*.json
```

## 八、一句话总结

`script/collect_data.py` 是 RoboTwin 的数据采集主入口：先通过多次仿真筛选成功 seed 并保存运动轨迹，再复用这些轨迹重新执行任务，保存多模态观测数据、场景信息和自然语言指令。
