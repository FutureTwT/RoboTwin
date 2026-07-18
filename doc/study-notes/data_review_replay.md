# RoboTwin 640×480 Replay 数据验证

## 验证范围

- 原始数据：/data1/common_data/RoboTwin2.0/dataset
- Replay 数据：/data1/sunyang/datasets/RoboTwin2.0_640_480/dataset
- 数据类型：aloha-agilex_clean_50
- 范围：full，50 个任务 × 50 个 episode
- 媒体：front/head/left/right 四路并行逐帧解码；head MP4 逐帧核对
- 耗时：59.1 分钟

## 验证结果

| 检查项 | 结果 | 数量或说明 |
| --- | --- | --- |
| 总体 | PASS | Python failures: 0 |
| 组织结构 | PASS | 50 tasks / 50 selected episodes |
| SHA256 文件对照 | PASS | 5100 |
| HDF5 数值对照 | PASS | 2500 files / 45000 datasets |
| 相机内参缩放 | PASS | 10000 datasets |
| 四路 RGB | PASS | 2209148 frame pairs，max MAE=4.0833 |
| Head MP4 | PASS | 552287 frames，max MAE=2.4854 |

## 失败统计

- 无。

## 结论

Replay 数据通过本次全量验证。
