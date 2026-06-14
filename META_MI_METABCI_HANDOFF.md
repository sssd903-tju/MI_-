# 跳一跳 × Meta MI / MetaBCI 交接说明

本文档用于项目交接与联调，明确游戏侧与 Meta MI/MetaBCI 侧的职责边界、通信协议、时序规则、验收标准与故障排查流程。

## 1. 交接目标

将本项目作为可插拔 MI 游戏范式运行：

- 游戏侧负责：连接、协议解析、动作状态机与玩法反馈。
- Meta MI / MetaBCI 侧负责：数据采集、信号处理、模型推理、标签与置信度输出。

这样可以做到：

- Python 算法迭代全部在 MetaBCI 工程内完成。
- 游戏工程无需修改即可接入不同 MI 算法实现。

## 2. 责任边界

### 2.1 游戏侧（当前项目）

- 接收 websocket 输入包（离线/在线）。
- 兼容多字段协议并统一归一化标签。
- 基于阈值和确认次数触发手柄动作（蓄力、释放、空中二跳）。
- 向上游回传游戏状态包（mi_status）用于闭环调参。

实现位置：

- [scripts/Game.gd](scripts/Game.gd)

### 2.2 Meta MI / MetaBCI 侧

- 采集 EEG/MI 数据并完成预处理。
- 完成在线推理并输出 label/confidence（或 class_id）。
- 维护时间戳和序号一致性，稳定发送数据流。

## 3. 通信拓扑

- 游戏读取输入：
  - 离线输入 ws 地址：ws://127.0.0.1:8766
  - 在线输入 ws 地址：ws://127.0.0.1:8767
- 游戏回传状态：
  - 回传到同一连接，消息类型为 mi_status

地址可通过 settings 覆盖（见第 7 节）。

## 4. 输入协议（Meta 侧 -> 游戏侧）

游戏侧支持“字段候选”解析，你可按 MetaBCI 现有输出选择任一字段名。

### 4.1 序号字段（任选其一）

- seq
- sequence
- id

规则：

- 若存在序号，游戏会做乱序检测。
- 若发送端重启并从 1 重新计数，游戏允许恢复。

### 4.2 时间戳字段（任选其一）

- timestamp_ms
- ts_ms
- timestamp
- ts
- time

规则：

- 游戏按毫秒比较新鲜度。
- 若值看起来是秒级时间戳，游戏会自动乘 1000 转毫秒。
- 超过 TTL（当前 1500ms）会被判定为过期包并丢弃。

### 4.3 标签字段（任选其一）

- label
- mi_label
- command
- state

标签归一化（游戏内部仅保留 hand / foot / rest）：

- hand 同义：right_hand, right, rh
- foot 同义：feet, left_hand, left, lh
- rest 同义：idle, none, neutral

### 4.4 类别编号回退（无 label 时）

类别字段候选：

- class_id
- label_id
- class

默认映射：

- 0 -> rest
- 1 -> hand
- 2 -> foot

可在 settings 中重映射。

### 4.5 置信度字段（任选其一）

- confidence
- conf
- prob
- score

规则：

- 游戏会 clamp 到 [0, 1]。
- 缺省时按 1.0 处理。

### 4.6 最小推荐包

{
  "seq": 1001,
  "timestamp_ms": 1760000123456,
  "label": "hand",
  "confidence": 0.86
}

## 5. 游戏状态回传协议（游戏侧 -> Meta 侧）

回传包示例：

{
  "type": "mi_status",
  "timestamp_ms": 1760000123999,
  "score": 14,
  "airborne": false,
  "charging": true,
  "mi_state": 1,
  "control_mode": 1,
  "mi_input_mode": 0
}

字段说明：

- score：当前得分
- airborne：玩家是否在空中
- charging：是否处于蓄力
- mi_state：MI 状态机枚举值（IDLE/CHARGING/REST_KEEPALIVE/AIRBORNE）
- control_mode：MANUAL 或 MI
- mi_input_mode：OFFLINE 或 ONLINE

建议 Meta 侧用途：

- 观察误触发时机（例如 airborne 期间输出 foot 导致无效动作）。
- 根据 score 或 mi_state 做自适应阈值与策略调整。

## 6. 关键判定参数（游戏侧当前值）

- 包 TTL：1500ms
- hand 阈值：0.70
- foot 阈值：0.72
- online 模式确认次数：
  - hand: 3
  - foot: 2
- offline 模式确认次数：
  - hand/foot 均按 1 处理
- mi_status 回传间隔：0.1s

如果 Meta 侧希望改参数，优先在游戏侧统一调整，避免算法与玩法阈值双向漂移。

## 7. 可配置项（settings）

settings 文件：user://settings.json

MI 相关键：

- mi_offline_ws_url
- mi_online_ws_url
- mi_class_id_to_label

示例：

{
  "mi_offline_ws_url": "ws://127.0.0.1:8766",
  "mi_online_ws_url": "ws://127.0.0.1:8767",
  "mi_class_id_to_label": {
    "0": "rest",
    "1": "hand",
    "2": "foot"
  }
}

## 8. 联调流程（推荐）

### 第一步：协议连通性

- Meta 侧先按最小包格式发送固定 rest。
- 游戏应稳定进入 MI 待机，不触发动作。

### 第二步：动作触发验证

- 连续发送 hand（满足阈值与确认次数）应触发蓄力。
- 发送 foot 应触发释放（地面）或二跳（空中）。
- 发送 rest 应可进入保活/停充路径。

### 第三步：时序与稳定性

- 人为注入过期时间戳，确认被丢弃。
- 人为打乱 seq，确认乱序计数增加。
- 重启发送端 seq 从 1，确认连接可恢复。

### 第四步：闭环观测

- Meta 侧订阅 mi_status，记录 score/mi_state 与输出标签关系。
- 依据误触发样本优化模型后处理（平滑、抑制、门控）。

## 9. 验收标准

满足以下即视为交接完成：

- 可以在不修改游戏代码前提下接入 MetaBCI 推理输出。
- 协议字段兼容通过（含 label 或 class_id 两条路径）。
- 10 分钟连续运行无连接异常导致的玩法中断。
- 动作触发符合预期：
  - hand -> 蓄力
  - foot -> 释放或空中二跳
  - rest -> 停充/保活
- Meta 侧可稳定接收 mi_status 反馈并用于调参。

## 10. 常见问题排查

### 问题 A：游戏无响应

检查顺序：

1. websocket 地址与端口是否一致。
2. 是否发送了可识别的 label 或 class_id。
3. confidence 是否低于阈值。
4. 时间戳是否过期。

### 问题 B：频繁误触发

建议：

1. 提高 Meta 侧输出稳定性（时间平滑/多数投票）。
2. 优先提升 foot 误检抑制。
3. 基于 mi_status 的 airborne/charging 做策略门控。

### 问题 C：动作延迟明显

建议：

1. 降低 Meta 侧窗口步长。
2. 检查发送频率是否低于 10Hz。
3. 核对时间戳来源是否统一为系统实时时钟。

## 11. 版本与维护建议

- 本交接文档作为协议基线。
- 新增字段时保持向后兼容，不删除既有候选字段。
- 若调整阈值或状态机逻辑，请同步更新本文档与变更记录。
