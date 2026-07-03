# demo_clean.yml 参数说明

本文整理 `task_config/demo_clean.yml` 中各参数的含义。该配置用于 RoboTwin 数据采集，整体属于“干净采集”配置：不开背景随机、不开桌面杂物、不开光照随机，默认保存 RGB、末端位姿和关节状态。

## 配置文件位置

```text
task_config/demo_clean.yml
```

对应运行示例：

```bash
bash collect_data.sh adjust_bottle demo_clean 0
```

其中 `demo_clean` 不需要带 `.yml` 后缀。

## 基础采集参数

| 参数 | 含义 |
|---|---|
| `render_freq: 0` | 渲染窗口刷新频率。`0` 表示不打开或不刷新 SAPIEN Viewer，适合无界面采集。 |
| `episode_num: 50` | 目标采集 episode 数量。 |
| `use_seed: false` | 是否复用已有 `seed.txt`。`false` 会先重新找成功 seed 并保存轨迹。 |
| `save_freq: 15` | 数据采集时每隔多少个仿真步保存一帧观测。 |
| `embodiment: [aloha-agilex]` | 使用的机器人本体配置。这里左右臂都用 `aloha-agilex`。 |
| `language_num: 100` | 采集结束后生成多少条语言指令描述。 |

## 随机化参数

| 参数 | 含义 |
|---|---|
| `random_background` | 是否随机桌面和墙面背景纹理。 |
| `cluttered_table` | 是否在桌面随机生成杂物。 |
| `clean_background_rate` | 使用干净背景的概率。只有 `random_background: true` 时才有意义。 |
| `random_head_camera_dis` | 随机扰动头部相机位置的最大距离。 |
| `random_table_height` | 随机扰动桌面高度。代码里会从 `[-value, 0]` 区间采样。 |
| `random_light` | 是否随机光照颜色。 |
| `crazy_random_light_rate` | 开启强随机光照扰动的概率。 |

## 相机参数

| 参数 | 含义 |
|---|---|
| `head_camera_type: D435` | 头部或静态相机型号，具体分辨率和视场角来自 `task_config/_camera_config.yml`。 |
| `wrist_camera_type: D435` | 腕部相机型号。 |
| `collect_head_camera: true` | 是否采集头部或静态相机。 |
| `collect_wrist_camera: true` | 是否采集左右腕部相机。 |

## 保存哪些观测

| 参数 | 含义 |
|---|---|
| `rgb: true` | 保存 RGB 图像。 |
| `third_view: false` | 是否保存额外 observer 第三视角 RGB。 |
| `depth: false` | 是否保存深度图。 |
| `pointcloud: false` | 是否保存点云。 |
| `observer: false` | 当前 `Base_Task.get_obs()` 中基本没有直接使用，像是遗留配置。 |
| `endpose: true` | 保存左右机械臂末端位姿和夹爪值。 |
| `qpos: true` | 保存左右臂关节状态和夹爪关节值。 |
| `mesh_segmentation: false` | 是否保存 mesh 级分割。 |
| `actor_segmentation: false` | 是否保存 actor 级分割。 |

## 点云参数

| 参数 | 含义 |
|---|---|
| `pcd_down_sample_num: 1024` | 点云下采样到 1024 个点。只有 `pointcloud: true` 时才明显有用。 |
| `pcd_crop: true` | 是否裁剪点云到默认桌面附近范围。 |

## 保存与缓存

| 参数 | 含义 |
|---|---|
| `save_path: ./data` | 数据保存根目录。实际会拼成 `./data/<task_name>/<task_config>/`。 |
| `clear_cache_freq: 5` | 每隔多少个 episode 清理一次 SAPIEN cache。 |
| `collect_data: true` | 是否进入正式数据保存阶段，生成 hdf5、mp4 等数据文件。 |
| `eval_video_log: true` | 评测脚本中是否保存 eval 视频；采集脚本主要看 `collect_data` 和 `save_freq`。 |

