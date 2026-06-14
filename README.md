# 跳一跳 MI-BCI

基于前额叶 EEG 的运动想象脑机接口康复训练游戏。

想象左手/右手运动 → 脑电实时解码 → 角色跳跃方向控制 → 闭环神经反馈。

## 特性

- **双硬件支持**：消费级 Fp1/Fp2 头环 (LSL直连) + 自制 C3/C4/Fp1/Fp2 四通道电路板 (串口)
- **时域 FAA 特征**：α/β 频段 × 4子窗 Temporal FAA (8维)，70试次 LOO-CV **68.6%**
- **实时专注度**：(θ+α)/β 比率，游戏内三色进度条可视化
- **双事件协议**：trial_start/mi_task 实现脑电窗口精确对齐
- **一体化 GUI**：采集→训练→推理全流程图形界面

## 架构

```
硬件层  →  LSL数据流  →  信号处理  →  Temporal FAA(8d)  →  SVM-RBF  →  WebSocket  →  Godot游戏
头环/PCB     250Hz      带通+陷波    α/β × 4子窗FAA     68.6% LOO     8767端口    跳一跳
```

## 快速开始

### 依赖

```bash
pip install numpy scipy mne scikit-learn websockets pylsl pyqtgraph
```

### 启动在线推理

```bash
# 启动推理服务器
python python/fp1fp2_online.py --stream brain-cube-eeg --port 8767

# 打开 Godot 项目 → 控制=MI, MI输入=Online → 开始游戏
```

### 离线训练

```bash
python python/train_fp1fp2.py \
  --bdf data.bdf \
  --sessions data/live_trials/ \
  --output python/models/fp1fp2_model
```

### GUI

```bash
python python/mi_bci_gui.py
```

## 项目结构

```
├── python/
│   ├── fp1fp2_online.py         # 在线推理服务器
│   ├── fp1fp2_classifier.py     # 特征提取 + 分类器
│   ├── train_fp1fp2.py          # 离线训练
│   ├── mi_bci_gui.py            # GUI 界面
│   ├── replay_bdf_lsl.py        # BDF → LSL 回放
│   ├── eeg_reader_fast.py       # EEG 实时波形显示
│   └── models/fp1fp2_model/     # 训练好的模型
├── scripts/                     # Godot GDScript
│   ├── Game.gd                  # 主逻辑: WS, MI 状态机
│   ├── Player.gd                # 物理: 蓄力, 跳跃
│   └── managers/
│       ├── level_mode_manager.gd
│       ├── offline_train_manager.gd
│       └── data_logger.gd
├── scenes/                      # Godot 场景
├── data/                        # 训练数据样例
└── docs/
    ├── PROJECT_INTRO.md         # 项目介绍与创新点
    ├── DATA_LABEL_FLOW.md       # 数据流完整文档
    └── 参赛报告_完整版.md        # 完整技术报告
```

## 特征方法

| 方法 | 维度 | 公式 | LOO |
|------|------|------|-----|
| Temporal FAA | 8 | α/β FAA × 4子窗(500ms) | **68.6%** |
| Power (log) | 12 | ln(P_ch^band) | 67.1% |
| FAA+Power | 18 | 6频带FAA + 12频带logP | 64.3% |
| FAA | 6 | (FP2-FP1)/(FP2+FP1) | 61.4% |

## 专注度

$$Fatigue = \frac{P_\theta + P_\alpha}{P_\beta},\quad Focus = 100 - Fatigue$$

绿 (>70) / 黄 (40-70) / 红 (<40) 三色进度条，每秒更新。

## 引用

详见 [参赛报告_完整版.md](参赛报告_完整版.md)

## License

MIT
