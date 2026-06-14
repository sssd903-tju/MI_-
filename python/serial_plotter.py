#!/usr/bin/env python3
"""串口 EEG 实时绘图上位机 — 4通道滚动波形 + FFT
协议: AA + 12B(4ch×INT24 big-endian), 921600bps, ~250Hz
"""

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
import serial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

FRAME_HEADER = 0xAA
DISPLAY_CH = 4
BYTES_PER_CH = 3
FS = 250
HISTORY_S = 5
CH_NAMES = ["C3", "C4", "F3", "F4"]
CH_COLORS = ["#2196F3", "#F44336", "#4CAF50", "#FF9800"]

class SerialPlotter:
    def __init__(self, root):
        self.root = root
        self.root.title("EEG 实时绘图")
        self.root.geometry("1200x750")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.data = [np.zeros(HISTORY_S * FS) for _ in range(DISPLAY_CH)]
        self.t = np.linspace(-HISTORY_S, 0, HISTORY_S * FS)
        self.running = False
        self.data_queue = queue.Queue(maxsize=10000)
        self.sample_count = 0

        self.port_var = tk.StringVar(value="/dev/cu.usbserial-130")
        self.baud_var = tk.StringVar(value="921600")
        self.status_var = tk.StringVar(value="未连接")
        self.rate_var = tk.StringVar(value="0 fps")

        self._build_ui()
        self._scan_ports()

    def _build_ui(self):
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill="x", padx=5, pady=5)
        ttk.Label(ctrl, text="串口:").pack(side="left")
        self.port_combo = ttk.Combobox(ctrl, textvariable=self.port_var, width=25)
        self.port_combo.pack(side="left", padx=5)
        ttk.Button(ctrl, text="刷新", command=self._scan_ports, width=5).pack(side="left")
        ttk.Label(ctrl, text="波特率:").pack(side="left", padx=(10,0))
        ttk.Entry(ctrl, textvariable=self.baud_var, width=8).pack(side="left", padx=5)
        self.connect_btn = ttk.Button(ctrl, text="连接", command=self._toggle, width=8)
        self.connect_btn.pack(side="left", padx=10)
        ttk.Label(ctrl, textvariable=self.status_var, width=25).pack(side="left", padx=5)
        ttk.Label(ctrl, textvariable=self.rate_var, width=12).pack(side="left")
        ttk.Label(ctrl, text="范围:").pack(side="left", padx=(10,0))
        self.range_var = tk.StringVar(value="5")
        ttk.Combobox(ctrl, textvariable=self.range_var, values=["1","2","5","10","20"], width=3,
                      state="readonly").pack(side="left", padx=5)
        self.range_var.trace("w", lambda *a: self._update_ylim())

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=5, pady=5)
        wave_frame = ttk.Frame(nb)
        fft_frame = ttk.Frame(nb)
        nb.add(wave_frame, text="波形")
        nb.add(fft_frame, text="频谱")

        # Waveform
        self.fig_wave, self.axes = plt.subplots(DISPLAY_CH, 1, figsize=(10,6), sharex=True)
        self.fig_wave.subplots_adjust(left=0.08, right=0.98, top=0.97, bottom=0.08, hspace=0.15)
        self.lines = []
        for i, ax in enumerate(self.axes):
            line, = ax.plot(self.t, self.data[i], color=CH_COLORS[i], linewidth=0.5)
            self.lines.append(line)
            ax.set_ylabel(CH_NAMES[i], fontsize=8, color=CH_COLORS[i])
            ax.set_ylim(-50000, 50000)
            ax.grid(True, alpha=0.3)
            ax.tick_params(labelsize=7)
        self.axes[-1].set_xlabel("Time (s)")
        self.canvas = FigureCanvasTkAgg(self.fig_wave, wave_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.bg_wave = None

        # FFT
        self.fig_fft, self.ax_fft = plt.subplots(1,1, figsize=(10,4))
        self.fig_fft.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.1)
        self.fft_lines = []
        for i in range(DISPLAY_CH):
            line, = self.ax_fft.plot([],[], color=CH_COLORS[i], linewidth=0.8, label=CH_NAMES[i])
            self.fft_lines.append(line)
        self.ax_fft.set_xlim(0, 60)
        self.ax_fft.set_xlabel("Hz"); self.ax_fft.set_ylabel("Power")
        self.ax_fft.legend(fontsize=8); self.ax_fft.grid(True, alpha=0.3)
        self.canvas_fft = FigureCanvasTkAgg(self.fig_fft, fft_frame)
        self.canvas_fft.get_tk_widget().pack(fill="both", expand=True)

    def _scan_ports(self):
        import glob
        ports = (glob.glob("/dev/cu.usb*") + glob.glob("/dev/cu.wchusb*") +
                 glob.glob("/dev/cu.SLAB*") + glob.glob("/dev/ttyUSB*"))
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def _toggle(self):
        if self.running: self._stop()
        else: self._start()

    def _start(self):
        port = self.port_var.get()
        baud = int(self.baud_var.get())
        try:
            self.ser = serial.Serial(port, baud, timeout=0)
            self.ser.reset_input_buffer()
        except Exception as e:
            self.status_var.set(f"错误: {e}"); return
        self.running = True; self.sample_count = 0; self.t0 = time.monotonic()
        self.connect_btn.config(text="断开"); self.status_var.set(f"已连接 {port}")
        threading.Thread(target=self._read_serial, daemon=True).start()
        self._update_plot(50)  # 50ms = 20fps plot refresh

    def _stop(self):
        self.running = False
        if hasattr(self, 'ser'): self.ser.close()
        self.connect_btn.config(text="连接"); self.status_var.set("已断开")

    def _read_serial(self):
        buf = bytearray()
        while self.running:
            try:
                w = self.ser.in_waiting
                if w == 0:
                    time.sleep(0.002)
                    continue
                buf.extend(self.ser.read(w))
            except Exception:
                break

            i = 0; n = len(buf)
            while i < n - 13 and self.running:
                if buf[i] != FRAME_HEADER: i += 1; continue
                raw = buf[i+1:i+13]
                s = [int.from_bytes(raw[ch*3:(ch+1)*3], "big", signed=True) for ch in range(DISPLAY_CH)]
                if sum(1 for v in s if abs(v) < 8000000) >= 2:
                    try: self.data_queue.put_nowait(s)
                    except queue.Full: pass
                    i += 13
                else: i += 1
            buf = buf[i:] if i > 0 else buf
            if len(buf) > 131072: buf = buf[-65536:]

    def _update_plot(self, interval_ms=50):
        if not self.running: return

        # Drain queue — collect all new samples
        new = []
        while not self.data_queue.empty():
            try: new.append(self.data_queue.get_nowait())
            except queue.Empty: break

        if new:
            arr = np.array(new); n = len(arr)
            self.sample_count += n
            for ch in range(DISPLAY_CH):
                self.data[ch] = np.roll(self.data[ch], -n)
                self.data[ch][-n:] = arr[:, ch]
                self.lines[ch].set_ydata(self.data[ch])

            elapsed = time.monotonic() - self.t0
            if elapsed > 0:
                self.rate_var.set(f"{self.sample_count/elapsed:.0f} fps")

            # Redraw waveform
            self.canvas.draw_idle()

            # Update FFT every 1s
            if self.sample_count % max(1, int(FS)) == 0:
                self._update_fft()

        self.root.after(interval_ms, lambda: self._update_plot(interval_ms))

    def _update_fft(self):
        from scipy import signal as sig
        n_fft = min(FS*2, len(self.data[0]))
        for ch in range(DISPLAY_CH):
            x = self.data[ch][-n_fft:] - self.data[ch][-n_fft:].mean()
            f, p = sig.welch(x, FS, nperseg=min(256, n_fft//2))
            self.fft_lines[ch].set_data(f, p)
        self.ax_fft.relim(); self.ax_fft.autoscale_view(scalex=False)
        self.canvas_fft.draw_idle()

    def _update_ylim(self):
        try:
            r = float(self.range_var.get()) * 1000000
            for ax in self.axes: ax.set_ylim(-r, r)
        except ValueError: pass

    def _on_close(self):
        self._stop(); self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    SerialPlotter(root)
    root.mainloop()
