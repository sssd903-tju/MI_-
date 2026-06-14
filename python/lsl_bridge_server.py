"""LSL → WebSocket 实时MI桥接：读脑电 → 特征提取 → 分类 → 发包"""
import asyncio
import json
import time
import math

import websockets
import numpy as np
from pylsl import StreamInlet, resolve_byprop

HOST = "0.0.0.0"
PORT = 8767

# === LSL 流配置 ===
EEG_STREAM = "brain-cube-eeg"

# === 信号处理参数 ===
FS = 250              # 采样率，根据设备调整
WINDOW_S = 1.0        # 窗口长度(秒)
WINDOW_N = int(FS * WINDOW_S)
BAND = (8, 30)        # alpha+beta 频段 (Hz)

# === 分类阈值 ===
LEFT_IDX = 0           # 左侧电极: PO3 (index 0)
RIGHT_IDX = 6          # 右侧电极: PO4 (index 6)
THRESHOLD = 1.3        # 左右功率比阈值
SEND_INTERVAL = 0.15


class MIBridge:
    def __init__(self):
        self.buffer = []
        self.last_label = "rest"
        self.seq = 0

    def add_sample(self, sample):
        """累积样本"""
        ch_data = [sample[LEFT_IDX], sample[RIGHT_IDX]]
        self.buffer.append(ch_data)
        if len(self.buffer) > WINDOW_N:
            self.buffer.pop(0)

    def is_ready(self):
        return len(self.buffer) >= WINDOW_N

    def band_power(self, data):
        """简单带通功率：用滑动平均近似 8-30Hz 能量"""
        n = len(data)
        if n < 4:
            return 0.0
        # 一阶差分近似高通，抑制低频漂移
        diff = np.diff(data)
        return float(np.var(diff))

    def classify(self):
        """C3/C4 功率比分类"""
        c3 = [self.buffer[i][0] for i in range(len(self.buffer))]
        c4 = [self.buffer[i][1] for i in range(len(self.buffer))]
        p3 = self.band_power(c3)
        p4 = self.band_power(c4)
        if p4 < 1e-8 and p3 < 1e-8:
            return "rest", 0.0
        ratio = p3 / (p4 + 1e-8)
        conf = min(0.95, abs(math.log2(ratio + 1e-8)) / 4)

        if ratio > THRESHOLD:
            return "left", conf
        elif ratio < 1.0 / THRESHOLD:
            return "right", conf
        return "rest", conf * 0.5


bridge = MIBridge()


async def handler(websocket):
    print("游戏已连接，查找LSL流...")
    streams = resolve_byprop("name", EEG_STREAM, timeout=10.0)
    if not streams:
        print(f"未找到LSL流: {EEG_STREAM}")
        await websocket.send(json.dumps({"label": "rest", "confidence": 0, "seq": 0}))
        await websocket.close()
        return

    inlet = StreamInlet(streams[0])
    info = inlet.info()
    print(f"LSL: {info.name()} ch={info.channel_count()} fs={info.nominal_srate()}")

    bridge.buffer.clear()
    bridge.seq = 0

    try:
        while True:
            sample, ts = inlet.pull_sample(timeout=0.05)
            if sample is None:
                await asyncio.sleep(0.01)
                continue

            bridge.add_sample(sample)

            if bridge.is_ready():
                label, conf = bridge.classify()

                bridge.seq += 1
                packet = {
                    "seq": bridge.seq,
                    "timestamp_ms": int(time.time() * 1000),
                    "label": label,
                    "confidence": round(conf, 3),
                }
                await websocket.send(json.dumps(packet))
                bridge.last_label = label

            # 接收游戏状态
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=0.005)
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(SEND_INTERVAL)

    except websockets.exceptions.ConnectionClosed:
        print("游戏断开")


async def main():
    print(f"MI桥接 ws://{HOST}:{PORT}")
    print(f"LSL流: {EEG_STREAM}  |  L=PO3[{LEFT_IDX}] R=PO4[{RIGHT_IDX}]  阈值={THRESHOLD}")
    async with websockets.serve(handler, HOST, PORT, max_size=2**20):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
