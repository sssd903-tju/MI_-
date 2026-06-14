# 跳一跳 MI-BCI

基于前额叶 EEG 头环（FP1/FP2）的运动想象脑机接口游戏。想象左手/右手运动 → 角色跳跃方向。

## 快速开始

### 硬件
- Brain Cube 8ch EEG 放大器 + FP1/FP2 头环
- macOS / Linux

### 依赖
```bash
conda create -n bci python=3.11
conda activate bci
pip install numpy scipy mne scikit-learn websockets pylsl pyqtgraph pyserial
```

### 启动

```bash
# 1. 启动串口→LSL 桥接（GUI 或命令行）
python python/mi_bci_gui.py
# 在线推理 tab → 选择串口 → 启动串口桥接

# 2. 启动 MI 在线推理
python python/fp1fp2_online.py \
  --stream brain-cube-eeg --port 8767 \
  --model python/models/fp1fp2_model

# 3. 打开 Godot 项目 → 控制=MI, MI输入=Online → 开始
```

### 离线训练
```bash
python python/train_fp1fp2.py \
  --bdf /path/to/data.bdf \
  --sessions data/bdf_trials/ \
  --output python/models/fp1fp2_model
```

## 项目结构

```
├── python/
│   ├── fp1fp2_classifier.py   # 核心：30维FAA特征 + SVM/RF/LDA分类器
│   ├── fp1fp2_online.py       # 在线推理服务器 (LSL → 分类 → WebSocket)
│   ├── train_fp1fp2.py        # 离线训练脚本
│   ├── mi_bci_gui.py          # GUI：串口桥接 + 信号监视 + 训练 + 推理
│   ├── mi_keyboard_sender.py  # 键盘模拟 MI 输入（离线测试用）
│   ├── replay_bdf_lsl.py      # BDF 文件回放为 LSL 流（测试用）
│   └── models/fp1fp2_model/   # 训练好的模型
├── scripts/                   # Godot GDScript
│   ├── Game.gd                # 主游戏逻辑：WS连接、MI状态机
│   ├── Player.gd              # 玩家物理：蓄力、跳跃
│   ├── Platform.gd            # 平台：普通/移动/脆弱
│   └── managers/
│       ├── level_mode_manager.gd     # 关卡模式
│       ├── offline_train_manager.gd  # 离线训练模式
│       └── data_logger.gd           # JSONL 数据记录
├── scenes/                    # Godot 场景文件
├── data/                      # 训练数据
│   ├── bdf_trials/            # BDF 离线采集数据
│   └── live_trials/           # 实时串口采集数据
├── PROJECT_INTRO.md           # 项目介绍与创新点
├── DATA_LABEL_FLOW.md         # 数据流与标签传输完整文档
└── README.md
```

## 技术要点

- **电极**：仅 2 通道 Fp1/Fp2（前额叶），消费级头环即可
- **特征**：多频带 FAA（前额叶 Alpha 不对称）+ 绝对功率（18 维）
- **分类器**：SVM-RBF（离线训练 LOOCV 71.8%）
- **协议**：trial_start → baseline(2s) → mi_task → task(2s) → classify
- **鲁棒性**：z-score 窗口归一化实现跨设备迁移
- **疲劳检测**：(θ+α)/β 比率实时显示专注度

## 引用

详见 [PROJECT_INTRO.md](PROJECT_INTRO.md)
