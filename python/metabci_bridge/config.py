"""Configuration constants for MI classification pipeline."""

import json
from pathlib import Path

# === 设备 / 通道配置 (8-channel Brain Cube) ===
# T7 = index 4 (左颞, 运动皮层附近), T8 = index 5 (右颞)
CHANNEL_NAMES = ["PO3", "O1", "Fp2", "Fp1", "T7", "T8", "PO4", "O2"]
LEFT_CHANNEL = "T7"
RIGHT_CHANNEL = "T8"
LEFT_IDX = 4   # T7 — active electrode (motor cortex left)
RIGHT_IDX = 5   # T8 — active electrode (motor cortex right)
N_CHANNELS = 8

# === 信号处理参数 ===
FS = 250                # 采样率 (Hz)
NOTCH_FREQ = 50.0       # 工频 (Hz)
BANDPASS_LOW = 8.0      # alpha 下限
BANDPASS_HIGH = 30.0    # beta 上限
ALPHA_BAND = (8, 13)    # alpha 频段
BETA_BAND = (13, 30)    # beta 频段

# === 试次窗口参数 ===
MI_ONSET_S = 2.0        # trial_start 后 2s 进入 MI 任务期
MI_WINDOW_S = 4.0       # MI 任务窗长 (离线用满 4s)
ONLINE_WINDOW_S = 1.5   # 在线滑动窗长 (更快出结果)

# === 在线参数 ===
SEND_INTERVAL = 0.15    # 发包间隔 (s)
CLASSIFY_TIMEOUT = 2.0  # 在线分类时限 (s)

# === WebSocket ===
HOST = "0.0.0.0"
PORT = 8767              # 在线 MI 端口

# === LSL 流 ===
EEG_STREAM_NAME = "brain-cube-eeg"

# === 模型文件 ===
MODEL_DIR = Path(__file__).parent / "models"
MODEL_FILE = "mi_model.json"

# === 标签映射 (游戏协议) ===
# 分类器输出 → 游戏标签
LABEL_MAP = {
    0: "rest",
    1: "left",    # hand / left hand MI
    2: "right",   # foot / right hand MI
}
