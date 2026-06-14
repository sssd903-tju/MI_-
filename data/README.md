# 数据目录

## bdf_trials/
离线 BDF 采集的训练数据（sessions 10-14），使用 Brain Cube 放大器 + BDF 文件格式。

| Session | 文件 | 试次 | 说明 |
|---------|------|------|------|
| 10 | session_20260614_103*.jsonl (4 files) | 40 | FP1/FP2 头环，SVM 80% |
| 11 | session_11.jsonl | 10 | 试次11.bdf |
| 12 | session_12.jsonl | 10 | 试次12.bdf |
| 13 | session_13.jsonl | 10 | 试次13.bdf |
| 14 | session_14.jsonl | 10 | 试次14.bdf |

**对应 BDF 文件**：`/Users/sssd/Downloads/实验数据/试次1{0,1,2,3,4}.bdf`

**字段说明**（每行一个 JSON）：
- `type`: "trial"
- `trial_id`: 试次序号
- `layer`: 关卡层数 (1-10)
- `ground_truth`: "left" / "right"（正确跳跃方向）
- `mi_decision`: MI 分类结果
- `correct`: true/false
- `timestamp_trial_start_ms`: Unix 毫秒时间戳
- `timestamp_mi_task_ms`: MI 任务开始时间
- `timestamp_jump_ms`: 跳跃时间

## live_trials/
实时 Brain Cube 串口采集的训练数据（session 16），通过 LSL 桥接实时录制。

| Session | 文件 | 试次 | 说明 |
|---------|------|------|------|
| 16 | session_20260614_163*.jsonl (3 files) | 30 | 直播数据，SVM 63.3% |

**对应 BDF 文件**：`/Users/sssd/Downloads/实验数据/试次16.bdf`

## archive/
早期测试数据，仅作参考保留。
