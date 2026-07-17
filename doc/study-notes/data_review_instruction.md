# RoboTwin 文本指令审查

## 审查范围

- 数据目录：`/data1/common_data/RoboTwin2.0/dataset`
- 数据类型：`aloha-agilex_clean_50`
- 任务数量：50
- Episode 数量：2500
- 指令数量：500000
- 仅检查文本、场景资产和任务语义，不检查运动轨迹。

## 审查结果

| 审查项 | 结果 |
| --- | ---: |
| 场景资产无法匹配的指令 | 0 |
| 缺少数字资产描述文件 | 0 |
| 左右臂与 `scene_info.json` 冲突 | 272 |
| seen/unseen 完全相同指令 | 0 |
| 空指令 | 0 |
| 未替换占位符 | 0 |
| 超出任务模板长度要求 | 361506 |
| 多物体指令 | 300000 |

## seen / unseen

- 去除常用虚词后，seen 词汇 1385 个，unseen 词汇 677 个，词汇集合重合度为 39.8%。
- seen 独有高频词：`align`(3257)、`secure`(2711)、`grasp`(2643)、`slide`(2518)、`stick`(2301)、`beverage`(2202)、`away`(2060)、`ensure`(1937)、`shade`(1841)、`carry`(1754)
- unseen 独有高频词：`brown-rimmed`(5255)、`darkened`(5143)、`distinct`(1680)、`highlights`(1674)、`dining`(1669)、`drink-protecting`(1657)、`elongated`(1654)、`disc-shaped`(1640)、`deck`(1417)、`vents`(1231)

## 任务摘要

| 任务 | seen 名称 | unseen 名称 | 同名跨资产 | 左右臂冲突 | 其他文本问题 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `adjust_bottle` | 24 | 6 | 0 | 62 | 800 |
| `beat_block_hammer` | 12 | 3 | 0 | 0 | 0 |
| `blocks_ranking_rgb` | 0 | 0 | 0 | 0 | 0 |
| `blocks_ranking_size` | 0 | 0 | 0 | 0 | 0 |
| `click_alarmclock` | 24 | 6 | 0 | 0 | 0 |
| `click_bell` | 24 | 6 | 0 | 0 | 0 |
| `dump_bin_bigbin` | 55 | 15 | 3 | 0 | 0 |
| `grab_roller` | 24 | 6 | 0 | 0 | 0 |
| `handover_block` | 0 | 0 | 0 | 0 | 0 |
| `handover_mic` | 36 | 9 | 0 | 0 | 0 |
| `hanging_mug` | 123 | 29 | 10 | 0 | 0 |
| `lift_pot` | 12 | 3 | 0 | 0 | 0 |
| `move_can_pot` | 138 | 36 | 3 | 0 | 0 |
| `move_pillbottle_pad` | 59 | 15 | 1 | 0 | 0 |
| `move_playingcard_away` | 36 | 9 | 0 | 0 | 0 |
| `move_stapler_pad` | 79 | 21 | 4 | 0 | 0 |
| `open_laptop` | 120 | 31 | 10 | 0 | 108 |
| `open_microwave` | 23 | 6 | 1 | 0 | 129 |
| `pick_diverse_bottles` | 177 | 50 | 12 | 0 | 0 |
| `pick_dual_bottles` | 24 | 6 | 0 | 0 | 200 |
| `place_a2b_left` | 543 | 139 | 20 | 0 | 0 |
| `place_a2b_right` | 529 | 137 | 21 | 0 | 0 |
| `place_bread_basket` | 116 | 29 | 5 | 0 | 159 |
| `place_bread_skillet` | 103 | 27 | 5 | 0 | 0 |
| `place_burger_fries` | 141 | 36 | 3 | 0 | 0 |
| `place_can_basket` | 96 | 23 | 1 | 0 | 0 |
| `place_cans_plasticbox` | 96 | 23 | 1 | 0 | 0 |
| `place_container_plate` | 113 | 30 | 5 | 0 | 0 |
| `place_dual_shoes` | 122 | 33 | 9 | 0 | 865 |
| `place_empty_cup` | 24 | 6 | 0 | 0 | 0 |
| `place_fan` | 24 | 6 | 0 | 0 | 0 |
| `place_mouse_pad` | 35 | 9 | 1 | 0 | 3900 |
| `place_object_basket` | 128 | 32 | 5 | 0 | 0 |
| `place_object_scale` | 167 | 45 | 11 | 0 | 0 |
| `place_object_stand` | 282 | 71 | 19 | 210 | 0 |
| `place_phone_stand` | 70 | 17 | 3 | 0 | 0 |
| `place_shoe` | 98 | 27 | 9 | 0 | 2000 |
| `press_stapler` | 79 | 21 | 4 | 0 | 0 |
| `put_bottles_dustbin` | 48 | 12 | 0 | 0 | 0 |
| `put_object_cabinet` | 327 | 83 | 8 | 0 | 6 |
| `rotate_qrcode` | 46 | 12 | 2 | 0 | 0 |
| `scan_object` | 124 | 33 | 5 | 0 | 0 |
| `shake_bottle` | 164 | 47 | 12 | 0 | 700 |
| `shake_bottle_horizontally` | 164 | 47 | 12 | 0 | 200 |
| `stack_blocks_three` | 0 | 0 | 0 | 0 | 0 |
| `stack_blocks_two` | 0 | 0 | 0 | 0 | 0 |
| `stack_bowls_three` | 12 | 3 | 0 | 0 | 400 |
| `stack_bowls_two` | 12 | 3 | 0 | 0 | 0 |
| `stamp_seal` | 59 | 14 | 2 | 0 | 0 |
| `turn_switch` | 93 | 24 | 3 | 0 | 600 |

## 左右臂冲突索引

以下 index 是对应 `instructions/episode{N}.json` 中 seen 或 unseen 列表的 0-based index。

### `adjust_bottle`

- seen：62 条
  - `episode0`：`[0, 50]`
  - `episode1`：`[24, 74]`
  - `episode2`：`[38, 88]`
  - `episode3`：`[37, 87]`
  - `episode4`：`[19, 69]`
  - `episode5`：`[38, 88]`
  - `episode8`：`[38, 88]`
  - `episode9`：`[47, 97]`
  - `episode10`：`[28, 78]`
  - `episode11`：`[28, 78]`
  - `episode13`：`[28, 78]`
  - `episode14`：`[41, 91]`
  - `episode16`：`[12, 62]`
  - `episode17`：`[14, 64]`
  - `episode19`：`[20, 70]`
  - `episode21`：`[30, 80]`
  - `episode23`：`[32, 82]`
  - `episode24`：`[48, 98]`
  - `episode26`：`[48, 98]`
  - `episode27`：`[23, 73]`
  - `episode29`：`[26, 76]`
  - `episode31`：`[13, 63]`
  - `episode34`：`[5, 55]`
  - `episode35`：`[27, 77]`
  - `episode36`：`[45, 95]`
  - `episode38`：`[12, 62]`
  - `episode39`：`[48, 98]`
  - `episode41`：`[10, 60]`
  - `episode43`：`[42, 92]`
  - `episode45`：`[41, 91]`
  - `episode48`：`[4, 54]`
- unseen：0 条

### `place_object_stand`

- seen：0 条
- unseen：210 条
  - `episode0`：`[7, 17, 27, 37, 47, 57, 67, 77, 87, 97]`
  - `episode2`：`[5, 15, 25, 35, 45, 55, 65, 75, 85, 95]`
  - `episode8`：`[2, 12, 22, 32, 42, 52, 62, 72, 82, 92]`
  - `episode12`：`[7, 17, 27, 37, 47, 57, 67, 77, 87, 97]`
  - `episode13`：`[8, 18, 28, 38, 48, 58, 68, 78, 88, 98]`
  - `episode15`：`[1, 11, 21, 31, 41, 51, 61, 71, 81, 91]`
  - `episode16`：`[4, 14, 24, 34, 44, 54, 64, 74, 84, 94]`
  - `episode18`：`[5, 15, 25, 35, 45, 55, 65, 75, 85, 95]`
  - `episode26`：`[7, 17, 27, 37, 47, 57, 67, 77, 87, 97]`
  - `episode29`：`[6, 16, 26, 36, 46, 56, 66, 76, 86, 96]`
  - `episode31`：`[0, 10, 20, 30, 40, 50, 60, 70, 80, 90]`
  - `episode32`：`[8, 18, 28, 38, 48, 58, 68, 78, 88, 98]`
  - `episode36`：`[2, 12, 22, 32, 42, 52, 62, 72, 82, 92]`
  - `episode40`：`[9, 19, 29, 39, 49, 59, 69, 79, 89, 99]`
  - `episode41`：`[4, 14, 24, 34, 44, 54, 64, 74, 84, 94]`
  - `episode43`：`[5, 15, 25, 35, 45, 55, 65, 75, 85, 95]`
  - `episode44`：`[7, 17, 27, 37, 47, 57, 67, 77, 87, 97]`
  - `episode45`：`[1, 11, 21, 31, 41, 51, 61, 71, 81, 91]`
  - `episode47`：`[5, 15, 25, 35, 45, 55, 65, 75, 85, 95]`
  - `episode48`：`[3, 13, 23, 33, 43, 53, 63, 73, 83, 93]`
  - `episode49`：`[0, 10, 20, 30, 40, 50, 60, 70, 80, 90]`

## 结论

官方指令与场景资产的对应关系由本地规则全量检查；审查结果与任务摘要见上表。原始 `common_data` 未被修改。

左右臂冲突来自两个写死 `right arm` 的任务模板，并非 272 个独立的随机错误。每个 episode 的模板会先随机打乱，再循环复用至生成 100 条指令，因此错误 index 呈固定间隔：

- 根因模板 `description/task_instruction/adjust_bottle.json:23`：`Pick {A} head-up using the right arm`。
- 根因模板 `description/task_instruction/place_object_stand.json:67`：`Set {A} onto {B} using the right arm.`。
- `adjust_bottle` 的 seen 有 50 个模板，错误模板每个 episode 出现 2 次，index 为 `x` 和 `x+50`；31 个左臂 episode 共 `31 × 2 = 62` 条冲突，unseen 无冲突。
- `place_object_stand` 的 unseen 有 10 个模板，错误模板每个 episode 出现 10 次，index 为 `x, x+10, ..., x+90`；21 个左臂 episode 共 `21 × 10 = 210` 条冲突，seen 无冲突。
- 随机打乱只改变各 episode 的起始 index `x`；同一 episode 内的间隔保持不变。场景要求右臂时，模板中的 `right arm` 与场景一致，不计为冲突。
