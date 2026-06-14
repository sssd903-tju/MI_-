#!/usr/bin/env python3
"""串口 → LSL 桥接 (6通道 PCB)

帧格式: AA | ch0(3B) | ch1(3B) | ... | ch5(3B) | ...(ignore)
        每通道 3 字节 INT24 有符号，高字节在前 (big-endian)
        波特率 921600

LSL 流名: serial-eeg，供 mi_bci_gui.py 在线推理使用。

Usage:
    python serial_lsl_bridge.py [--port /dev/cu.usb*] [--name serial-eeg]
"""

import argparse
import sys
import time

import serial
from pylsl import StreamInfo, StreamOutlet

# ── 配置 ──
FRAME_HEADER = 0xAA
N_CHANNELS = 4
BYTES_PER_CH = 3      # 24-bit signed int
FS = 250             # 有效采样率
CH_NAMES = ["C3", "C4", "F3", "F4"]
MI_LEFT_IDX = 0   # C3 → 右手MI
MI_RIGHT_IDX = 1  # C4 → 左手MI
STREAM_NAME = "serial-eeg"


def find_serial_port():
    import glob
    candidates = (
        glob.glob("/dev/tty.usb*") + glob.glob("/dev/tty.wchusb*") +
        glob.glob("/dev/tty.SLAB*") + glob.glob("/dev/ttyUSB*") +
        glob.glob("/dev/cu.usb*")
    )
    return candidates[0] if candidates else None


def main():
    p = argparse.ArgumentParser(description="Serial → LSL EEG Bridge (6ch)")
    p.add_argument("--port", help="串口路径")
    p.add_argument("--name", default=STREAM_NAME, help="LSL 流名称")
    p.add_argument("--baud", type=int, default=921600)
    p.add_argument("--fs", type=float, default=250.0)
    args = p.parse_args()

    port = args.port or find_serial_port()
    if not port:
        print("未找到串口，用 --port 指定")
        sys.exit(1)

    print(f"串口: {port} @ {args.baud} baud")
    ser = serial.Serial(port, args.baud, timeout=0.1)

    info = StreamInfo(args.name, "EEG", N_CHANNELS, args.fs, "int32",
                      source_id=f"serial_{port}")
    ch_xml = info.desc().append_child("channels")
    for name in CH_NAMES:
        ch = ch_xml.append_child("channel")
        ch.append_child_value("label", name)
    outlet = StreamOutlet(info)

    print(f"LSL: {args.name} ({N_CHANNELS}ch @ {args.fs}Hz) {CH_NAMES}")
    print("Ctrl+C 停止")

    buf = bytearray()
    sample_count = 0
    t0 = time.time()

    try:
        while True:
            chunk = ser.read(ser.in_waiting or 1)
            if chunk:
                buf.extend(chunk)

            # Parse AA + 12B frames (4ch × 3B INT24 big-endian)
            i = 0
            buflen = len(buf)
            while i < buflen - 13:
                if buf[i] != FRAME_HEADER:
                    i += 1; continue
                raw = buf[i+1:i+13]
                samples = [int.from_bytes(raw[ch*BYTES_PER_CH:(ch+1)*BYTES_PER_CH], "big", signed=True) for ch in range(N_CHANNELS)]
                varying = sum(1 for v in samples if abs(v) < 8000000)
                if varying >= 2:
                    outlet.push_sample(samples)
                    sample_count += 1
                    i += 13
                else:
                    i += 1
            buf = buf[i:] if i > 0 else buf
            if len(buf) > 65536: buf = buf[-32768:]

            if sample_count > 0 and sample_count % 100 == 0:
                elapsed = time.time() - t0
                print(f"\r  样本: {sample_count}  "
                      f"速率: {sample_count/elapsed:.0f}Hz  "
                      f"ch0={samples[0]} ch1={samples[1]}",
                      end="", flush=True)

            time.sleep(0.002)

    except KeyboardInterrupt:
        print(f"\n停止。共 {sample_count} 样本")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
