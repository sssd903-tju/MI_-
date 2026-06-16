# MetaBCI 脑机接口游戏范式平台 — 架构总结与设计指南

> 本文档总结"跳一跳 MI-BCI"项目的核心设计模式和技术决策，为下一个工程——**基于 MetaBCI 的脑机接口游戏范式平台**——提供架构参考和复用指南。

## 1 当前项目总结

"跳一跳"是一套完整的 MI-BCI 神经康复训练游戏系统：玩家佩戴 Fp1/Fp2 前额叶头环，通过左右手运动想象控制角色跳跃方向。

### 核心技术指标

| 指标 | 值 |
|------|-----|
| 通道 | Fp1/Fp2 (2ch, 250Hz) |
| 特征 | Temporal FAA (α/β × 4子窗 × 500ms = 8维) |
| 分类器 | SVM-RBF (class_weight=balanced, C=1.0, γ=scale) |
| 离线 LOO-CV | **79.6%** (49 试次, 5 session) |
| 在线准确率 | **72.0%** (50 试次, 关卡模式) |
| 端到端延迟 | 60.8ms (≤200ms 指标) |
| 游戏引擎 | Godot 4.x (GDScript) |
| 后端 | Python (信号处理 + 分类 + WebSocket) |

## 2 游戏范式设计模式

### 2.1 两种游戏模式

当前项目沉淀了两种互补模式，新平台应直接复用：

**关卡模式 (Level Mode)** — 在线实时 MI 驱动：
```
箭头闪烁(2s, 方向提示) → 箭头隐藏(trial_start) → MI任务(≥2s) → 分类 → 跳跃
```
- 箭头闪烁期间：玩家不执行 MI，仅观察方向
- 箭头隐藏后：玩家开始运动想象，服务器收集数据、分类、回传结果
- 跳跃后：自动生成下一层平台（3 种类型：普通/移动/脆弱，难度自适应）

**离线训练模式 (Offline Training Mode)** — 标准化数据采集：
```
5 阶段试次协议 (10s/试次):
  START (0-2s)   → trial_start 发送, 箭头闪烁, 观察方向
  MI TASK (2-6s) → mi_task 发送, 箭头消失, 执行 MI
  JUMP (6-7s)    → 读取分类结果, 跳跃
  SCORE (7-8s)   → 落地反馈 (完美/普通/连击)
  RELAX (8-10s)  → 短暂休息
```
- 每个试次自动记录完整时间戳至 JSONL
- 5 阶段可视化进度条

### 2.2 新的游戏范式平台——扩展方向

作为平台，应支持多种 MI 范式（不止左右手）：

| 范式 | MI 类型 | 游戏映射 | 通道建议 |
|------|---------|---------|---------|
| 左右手 | 左手 vs 右手 | 左右跳跃 | C3/C4 或 Fp1/Fp2 |
| 手/脚 | 手 vs 脚 | 跳跃 vs 蹲下 | C3/C4 + Cz |
| 静息/运动 | rest vs MI | 静止 vs 移动 | Fp1/Fp2 |
| 多类 | 左手/右手/脚/舌头 | 四方向移动 | C3/C4/Cz/CP3/CP4 |

关键设计原则：
- **统一试次协议**：所有范式共用 5 阶段结构，仅 MI 任务类型不同
- **可配置事件**：trial_start / mi_task 时间可调（默认 2s/4s）
- **范式-特征映射**：不同范式自动选择对应通道和特征提取方法

## 3 LSL 数据流设计

### 3.1 为什么用 LSL

Lab Streaming Layer (LSL) 是 EEG 数据流的事实标准协议，核心优势：
- **硬件无关**：任何设备只要输出 LSL 流，上层代码零修改
- **时间同步**：<1ms 精度，支持多流同步
- **网络透明**：支持本地和远程传输
- **多语言**：Python/C++/MATLAB/Java 均有绑定

### 3.2 双硬件统一方案

```
设备A (消费级头环)          设备B (自制PCB)
  Fp1/Fp2, 250Hz             C3/C4/Fp1/Fp2, 250Hz
  LSL直连                    串口 → serial_lsl_bridge.py → LSL
       ↓                              ↓
       └──────── LSL Stream ──────────┘
                    ↓
            fp1fp2_online.py (--stream 参数切换)
                    ↓
              Godot Game
```

### 3.3 LSL 流命名规范

```
brain-cube-eeg   → 消费级头环 (Fp1/Fp2, 8ch, 250Hz)
serial-eeg       → 自制电路板 (C3/C4/Fp1/Fp2, 4ch, 250Hz)
```

新平台建议统一为：`metabci-game-{device_type}-eeg`

### 3.4 WebSocket 协议

**游戏 → 服务器 (事件)**：
```json
{"type": "trial_start", "layer": 1, "ground_truth": "left"}
{"type": "mi_status", "score": 5, "airborne": false, "mi_state": 1}
```

**服务器 → 游戏 (分类结果)**：
```json
{"seq": 1, "timestamp_ms": 1718000000000, "label": "left", "confidence": 0.72, "fatigue": 35}
```

**服务器 → 游戏 (专注度, 1Hz 独立推送)**：
```json
{"type": "fatigue", "fatigue": 35}
```

端口约定：8767 (在线推理), 8766 (离线模拟), 8765 (难度自适应, 预留)。

## 4 Godot-Python 集成方案

### 4.1 架构

```
Godot 4.x (GDScript)                    Python
  ├── WebSocket 客户端 ←────────→  WebSocket 服务器 (:8767)
  │   (Game.gd)                    (fp1fp2_online.py)
  │                                    ├── LSL 数据接收
  │                                    ├── 信号处理 (滤波+特征)
  │                                    ├── 分类推理 (模型加载)
  │                                    └── 专注度计算
  │
  ├── JSONL 数据记录
  │   (data_logger.gd)
  │
  └── GUI 模式切换
      (双语/难度/控制模式)
```

### 4.2 关键 Godot 文件

| 文件 | 职责 |
|------|------|
| `Game.gd` | WebSocket 连接管理、MI 标签处理、状态机、HUD 刷新 |
| `Player.gd` | 角色物理：蓄力、跳跃、空中跳跃、碰撞响应 |
| `Platform.gd` | 平台：普通/移动/脆弱、宽度自适应、支撑检测 |
| `level_mode_manager.gd` | 关卡模式：箭头引导、方向计算、trial_start/mi_task 事件 |
| `offline_train_manager.gd` | 离线训练：5 阶段协议、数据标注、JSONL 记录 |
| `data_logger.gd` | JSONL 追加写入、会话管理 |

### 4.3 Godot WebSocket 要点

```gdscript
# 连接
var mi_ws: WebSocketPeer = WebSocketPeer.new()
mi_ws.connect_to_url("ws://127.0.0.1:8767")

# 轮询接收
mi_ws.poll()
while mi_ws.get_available_packet_count() > 0:
    var packet = mi_ws.get_packet()
    var data = JSON.parse_string(packet.get_string_from_utf8())

# 发送
mi_ws.send_text(JSON.stringify({"type": "trial_start", ...}))

# 重连
const MI_RECONNECT_INTERVAL: float = 0.75  # 秒
```

### 4.4 Python 服务器要点

```python
# LSL 连接
from pylsl import StreamInlet, resolve_byprop
streams = resolve_byprop("name", "brain-cube-eeg", timeout=10.0)
inlet = StreamInlet(streams[0])

# 拉取数据
chunk, ts = inlet.pull_chunk(timeout=0.05, max_samples=40)

# WebSocket
import websockets
async with websockets.serve(handler, "0.0.0.0", 8767):
    await asyncio.Future()

# 信号处理流水线
data → 0.5-45Hz Butterworth(4阶) → 50Hz IIR陷波 → z-score窗口归一化
     → Temporal FAA(α/β × 4子窗 × 500ms) → SVM-RBF → {label, confidence}
```

## 5 特征提取与分类

### 5.1 特征拓扑

```
Temporal FAA (当前最优, 8维, 79.6% LOO):
  FAA_alpha_t0  FAA_alpha_t1  FAA_alpha_t2  FAA_alpha_t3    (8-13Hz, 4子窗)
  FAA_beta_t0   FAA_beta_t1   FAA_beta_t2   FAA_beta_t3     (13-30Hz, 4子窗)
  
FAA (6维, 67.3%):
  6频带 FAA指标: θ, α, low-β, high-β, β, broadband

FAA+Power (18维, 65.3%):
  FAA(6) + logPower(12)
```

### 5.2 频带定义

```python
BANDS = {
    "theta": (4, 8), "alpha": (8, 13),
    "low_beta": (13, 20), "high_beta": (20, 30),
    "beta": (13, 30), "broadband": (0.5, 30)
}
```

### 5.3 分类器选型依据

| 分类器 | Fp1/Fp2 LOO | C3/C4 (BCI IV-2b) | 特点 |
|--------|-----------|-------------------|------|
| **SVM-RBF** | **79.6%** | 76.5% (FBCSP) | 非线性，小样本友好 |
| LDA | 61.2% | 66.7% (CSP) | 线性，计算快，在线首选 |
| RF | 63.3% | 71.8% | 易过拟合 |

> Fp1/Fp2 的 FAA 特征空间是非线性可分的（SVM 对 LDA 提升 +18.4%），而 C3/C4 的 CSP 空间近似线性（SVM 仅 +0-3%）。这决定了**不同通道应使用不同的分类器策略**。

## 6 数据管理

### 6.1 目录结构（建议新平台沿用）

```
data/
├── bdf_trials/          # 离线训练用 BDF + JSONL
├── live_trials/         # 在线测试用 JSONL
└── models/              # 训练好的模型 (JSON + pickle)
```

### 6.2 JSONL 格式

```json
{"type": "session_start", "timestamp_ms": ..., "total_layers": 10, "mode": "offline_train"}
{"type": "trial", "trial_id": 1, "layer": 2, "ground_truth": "left",
 "timestamp_trial_start_ms": ..., "timestamp_mi_task_ms": ..., "correct": true}
{"type": "session_end", "total_trials": 10, "trials": [...]}
```

## 7 专注度检测

公式：`Fatigue = (Pθ + Pα) / Pβ`，映射到 0-100。

游戏 HUD：绿(>70) / 黄(40-70) / 红(<40) 三色进度条，每秒独立推送（`{"type":"fatigue"}`）。

## 8 新平台推荐的架构演进

### 8.1 从单游戏到平台

```
当前 (跳一跳):
  python/fp1fp2_online.py (单文件, 硬编码流名和端口)
  Godot 场景 (单游戏)

新平台 (MetaBCI 游戏范式平台):
  python/metabci_platform/
    ├── server.py           # 统一推理服务器 (支持多范式切换)
    ├── classifier.py       # 分类器工厂 (Fp1_FAA / C3_CSP / Fp1C3_Hybrid)
    ├── feature.py          # 特征提取库 (TemporalFAA / CSP / ERD / Power)
    ├── fatigue.py          # 专注度检测
    └── lsl_bridge.py       # LSL 流管理 (多设备注册)
  
  godot/metabci_games/
    ├── core/               # 共享框架
    │   ├── ws_client.gd    # WebSocket 客户端 (Game.gd 通用版)
    │   ├── trial_protocol.gd  # 5 阶段试次协议
    │   └── data_logger.gd  # JSONL 记录
    ├── jump_game/          # 跳一跳 (复用)
    ├── runner_game/        # 跑步游戏 (新)
    ├── rhythm_game/        # 节奏游戏 (新)
    └── game_selector.tscn  # 游戏选择菜单
```

### 8.2 推荐优先实现的新游戏范式

1. **跑步游戏**：持续 MI 控制速度，rest 停止——测试连续分类
2. **节奏游戏**：固定节奏提示 MI，错过节奏扣分——提升 MI 时间精度
3. **双人对战**：两个玩家同时 MI，先完成目标者胜——社交激励

## 9 关键经验教训

1. **Temporal 特征 > 静态特征**：500ms 子窗 FAA 比整窗平均高 12.3%（67.3%→79.6%）
2. **离线≠在线**：离线→在线衰减约 5-15%，在线测试不可省略
3. **Session 质量差异巨大**：同一被试不同 session 准确率可从 50% 到 90%
4. **专注度检测是功能放大器**：不是为了精度，是为了让被试"看到自己的状态"
5. **z-score 窗口归一化是跨设备迁移的关键**：BDF(0.5V) vs ADC(866k) 差异 6 个数量级，一行归一化解决
6. **双事件协议是数据标注的基石**：trial_start + mi_task 自动对齐脑电窗口
7. **Godot WebSocket 需要手动 polling**：必须在 `_physics_process` 中调用 `mi_ws.poll()`
8. **模型文件用 JSON+pickle 混合**：JSON 存元数据（人类可读），pickle 存分类器（机器高效）

## 10 关键配置文件速查

| 文件 | 关键常量 |
|------|---------|
| `fp1fp2_online.py` | `FS=250`, `FP1_IDX=4, FP2_IDX=5`, `BUFFER_N=1000`, `LSL_STREAM` |
| `Game.gd` | `MI_HAND_CONF_THRESHOLD=0.50`, `MI_PACKET_TTL_MS=1500`, `MI_RECONNECT_INTERVAL=0.75` |
| `level_mode_manager.gd` | `ARROW_HINT_DURATION=2.0`, `IDLE_TIMEOUT=5.0` |
| `offline_train_manager.gd` | `CYCLE_DURATION=10.0`, `PHASE_START_END=2.0`, `PHASE_MI_TASK_END=6.0` |
