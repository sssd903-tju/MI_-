#!/usr/bin/env python3
"""Online MI inference server — LSL → clean → classify → WebSocket → 游戏.

Usage:
    python -m metabci_bridge.main_online [--host 0.0.0.0] [--port 8767]
                                         [--stream brain-cube-eeg]
                                         [--model models/mi_model.json]
"""

import argparse
import asyncio
import json
import logging
import math
import time
from collections import deque
from pathlib import Path

import numpy as np
import websockets
from scipy.integrate import trapezoid
from scipy import signal as sig
from pylsl import StreamInlet, resolve_byprop

from . import config
from .preprocess import Preprocessor
from .feature_extractor import FeatureExtractor
from .classifier import MIClassifier

logger = logging.getLogger(__name__)

# ── Online state machine ──


class OnlineMIProcessor:
    """Real-time MI classification — trial-based protocol.

    Protocol (per trial):
      1. Game sends trial_start event
      2. Collect baseline window:  [trial_start, trial_start + 1s]
      3. Collect task window:      [trial_start + 1s, trial_start + 3s]
      4. Compute ERD features (task vs baseline)
      5. Classify → send one result packet to game

    Also supports continuous fallback when no model is loaded.
    """

    BASELINE_S = 2.0
    TASK_S = 2.0

    def __init__(
        self,
        fs: float = config.FS,
        send_interval: float = config.SEND_INTERVAL,
    ):
        self.fs = fs
        self.baseline_n = int(fs * self.BASELINE_S)
        self.task_n = int(fs * self.TASK_S)
        self.send_interval = send_interval

        # Continuous buffer (for pre-trial background collection)
        self.ring_buffer: deque[np.ndarray] = deque(maxlen=int(fs * 5.0))
        self.seq: int = 0
        self.last_label: str = "rest"

        # Processing
        self.preprocessor = Preprocessor(fs=fs)
        self.extractor = FeatureExtractor(fs=fs)

        # Classifier (loaded from model file)
        self.classifier: MIClassifier | None = None
        self.use_erd: bool = False

        # Trial state
        self.current_trial: dict | None = None
        self.trial_baseline: list = []   # baseline samples for current trial
        self.trial_task: list = []       # task samples for current trial
        self.trial_baseline_done: bool = False
        self.trial_task_done: bool = False
        self.trial_result: tuple | None = None  # (label, conf)

        # Session log
        self.session_log: list[dict] = []
        self.session_start_ms: int = int(time.time() * 1000)

    def load_model(self, model_path: str | Path) -> None:
        """Load pre-trained classifier. Auto-detects ERD vs band-power."""
        try:
            self.classifier = MIClassifier.load(model_path)
            self.use_erd = (self.classifier._n_features == 9)
            logger.info(
                "Loaded %s classifier from %s (%d features)",
                "ERD" if self.use_erd else "band-power",
                model_path,
                self.classifier._n_features,
            )
        except FileNotFoundError:
            logger.warning(
                "No pre-trained model at %s — using threshold-based fallback",
                model_path,
            )
            self.classifier = None
            self.use_erd = False

    def add_sample(self, sample: np.ndarray) -> None:
        """Feed one EEG sample. Routes to baseline or task buffer if trial active."""
        arr = np.asarray(sample, dtype=np.float64)
        self.ring_buffer.append(arr)

        if self.current_trial is None:
            return

        if not self.trial_baseline_done:
            self.trial_baseline.append(arr)
            if len(self.trial_baseline) >= self.baseline_n:
                self.trial_baseline_done = True
                logger.debug("Baseline complete: %d samples", len(self.trial_baseline))
        elif not self.trial_task_done:
            self.trial_task.append(arr)
            if len(self.trial_task) >= self.task_n:
                self.trial_task_done = True
                logger.debug("Task complete: %d samples", len(self.trial_task))
                # Auto-classify when task window is full
                self.trial_result = self._classify_erd_trial()

    def is_ready(self) -> bool:
        """Check if a trial is active and ready."""
        return self.current_trial is not None

    def classify(self) -> tuple[str, float]:
        """Get pending trial classification result.

        Returns:
            (label, confidence), or ("rest", 0.0) if no result yet
        """
        if self.trial_result is not None:
            result = self.trial_result
            self.trial_result = None
            return result
        return "rest", 0.0

    def _classify_erd_trial(self) -> tuple[str, float]:
        """Compute ERD features from baseline + task windows and classify."""
        if len(self.trial_baseline) < 64 or len(self.trial_task) < 64:
            return "rest", 0.1

        bl_data = np.array(self.trial_baseline).T  # (n_ch, n_baseline)
        tk_data = np.array(self.trial_task).T       # (n_ch, n_task)

        def bp(x, low, high):
            nperseg = min(128, len(x) // 2)
            if nperseg < 32:
                nperseg = len(x) // 4
            f, p = sig.welch(x, self.fs, nperseg=nperseg)
            mask = (f >= low) & (f <= high)
            if mask.sum() < 2:
                return 0.0
            return float(trapezoid(p[mask], f[mask]))

        t7_idx = config.LEFT_IDX
        t8_idx = config.RIGHT_IDX

        t7_bl = bl_data[t7_idx] - bl_data[t7_idx].mean()
        t8_bl = bl_data[t8_idx] - bl_data[t8_idx].mean()
        t7_tk = tk_data[t7_idx] - tk_data[t7_idx].mean()
        t8_tk = tk_data[t8_idx] - tk_data[t8_idx].mean()

        # Broadband ERD
        bl_t7 = bp(t7_bl, 0.5, 30); tk_t7 = bp(t7_tk, 0.5, 30)
        bl_t8 = bp(t8_bl, 0.5, 30); tk_t8 = bp(t8_tk, 0.5, 30)
        erd_t7 = (tk_t7 - bl_t7) / (bl_t7 + 1e-15)
        erd_t8 = (tk_t8 - bl_t8) / (bl_t8 + 1e-15)
        lateral = erd_t7 - erd_t8

        # Alpha ERD
        a_bl_t7 = bp(t7_bl, 8, 13); a_tk_t7 = bp(t7_tk, 8, 13)
        a_bl_t8 = bp(t8_bl, 8, 13); a_tk_t8 = bp(t8_tk, 8, 13)
        erd_a_t7 = (a_tk_t7 - a_bl_t7) / (a_bl_t7 + 1e-15)
        erd_a_t8 = (a_tk_t8 - a_bl_t8) / (a_bl_t8 + 1e-15)
        lateral_a = erd_a_t7 - erd_a_t8

        # Beta ERD
        b_bl_t7 = bp(t7_bl, 13, 30); b_tk_t7 = bp(t7_tk, 13, 30)
        b_bl_t8 = bp(t8_bl, 13, 30); b_tk_t8 = bp(t8_tk, 13, 30)
        erd_b_t7 = (b_tk_t7 - b_bl_t7) / (b_bl_t7 + 1e-15)
        erd_b_t8 = (b_tk_t8 - b_bl_t8) / (b_bl_t8 + 1e-15)
        lateral_b = erd_b_t7 - erd_b_t8

        features = np.array([erd_t7, erd_t8, lateral,
                            erd_a_t7, erd_a_t8, lateral_a,
                            erd_b_t7, erd_b_t8, lateral_b])

        if self.classifier is not None and self.classifier._trained:
            score = self.classifier.decision_function(features)
            label_idx = int(score >= 0)
            label = config.LABEL_MAP.get(
                self.classifier._classes[label_idx], "rest")
            conf = min(0.95, 1.0 / (1.0 + math.exp(-abs(score))))
        else:
            # Threshold fallback: erds > 0 → left (T7 suppressed = right MI)
            label, conf = "rest", 0.1
            if lateral > 0.05:
                label, conf = "left", min(0.9, abs(lateral) * 2)
            elif lateral < -0.05:
                label, conf = "right", min(0.9, abs(lateral) * 2)

        return label, round(conf, 3)

    def handle_game_event(self, event: dict) -> None:
        """Process event from game WebSocket.

        trial_start: begin new trial (2s baseline + 2s task → classify)
        session_end: save session log
        """
        ev_type = event.get("type", "")

        if ev_type == "trial_start":
            self.current_trial = event
            # Collect baseline from data AFTER trial_start (matches offline)
            self.trial_baseline = []
            self.trial_baseline_done = False
            self.trial_task = []
            self.trial_task_done = False
            self.trial_result = None
            logger.info(
                "trial_start: layer=%s gt=%s baseline=%d samples",
                event.get("layer"), event.get("ground_truth"),
                len(self.trial_baseline),
            )

        elif ev_type == "session_end":
            # Save session log alongside model
            self._save_session_log(event)
            logger.info(
                "session_end: %d trials received",
                len(event.get("trials", [])),
            )

        elif ev_type == "response":
            logger.debug(
                "game response: dir=%s correct=%s",
                event.get("direction"), event.get("correct"),
            )

        elif ev_type == "result":
            logger.debug("game result: correct=%s", event.get("correct"))

    def _save_session_log(self, event: dict) -> None:
        """Save session log to disk."""
        log_dir = config.MODEL_DIR / "sessions"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = log_dir / f"session_{ts}.json"
        path.write_text(json.dumps(event, indent=2, ensure_ascii=False))
        logger.info("Session log saved: %s", path)

    def build_packet(self, label: str, conf: float) -> dict:
        """Build WebSocket control packet for game."""
        self.seq += 1
        return {
            "seq": self.seq,
            "timestamp_ms": int(time.time() * 1000),
            "label": label,
            "confidence": conf,
        }


# ── WebSocket handler ──


async def handle_connection(
    websocket: websockets.WebSocketServerProtocol,
    processor: OnlineMIProcessor,
) -> None:
    """Handle one game connection."""
    peer = websocket.remote_address
    logger.info("Game connected from %s:%s", *peer)

    # Connect to LSL
    logger.info("Searching for LSL stream: %s", config.EEG_STREAM_NAME)
    streams = resolve_byprop("name", config.EEG_STREAM_NAME, timeout=10.0)
    if not streams:
        logger.error("LSL stream not found: %s", config.EEG_STREAM_NAME)
        await websocket.send(json.dumps({
            "label": "rest", "confidence": 0, "seq": 0,
        }))
        await websocket.close()
        return

    inlet = StreamInlet(streams[0])
    info = inlet.info()
    logger.info(
        "LSL connected: %s ch=%d fs=%.0f",
        info.name(), info.channel_count(), info.nominal_srate(),
    )

    # Reset processor state
    processor.seq = 0
    processor.last_label = "rest"
    processor.current_trial = None
    processor.trial_baseline = []
    processor.trial_task = []
    processor.trial_baseline_done = False
    processor.trial_task_done = False
    processor.trial_result = None
    processor.session_start_ms = int(time.time() * 1000)
    processor.ring_buffer.clear()

    last_send = 0.0
    trial_phase = "idle"  # idle | baseline | task | done

    try:
        while True:
            # Pull LSL chunk (buffered, more reliable)
            chunk, chunk_ts = inlet.pull_chunk(timeout=0.05, max_samples=40)
            if chunk:
                for sample in chunk:
                    processor.add_sample(sample)

            # Trial progress logging
            if processor.current_trial:
                if not processor.trial_baseline_done:
                    n = len(processor.trial_baseline)
                    if n > 0 and n % 125 == 0:
                        logger.debug("Baseline: %d/%d", n, processor.baseline_n)
                elif not processor.trial_task_done:
                    n = len(processor.trial_task)
                    if n > 0 and n % 125 == 0:
                        logger.debug("Task: %d/%d", n, processor.task_n)

            # Check for trial result
            if processor.current_trial and processor.trial_task_done:
                label, conf = processor.classify()
                if label != "rest" or conf > 0.3:
                    packet = processor.build_packet(label, conf)
                    await websocket.send(json.dumps(packet))
                    logger.info(
                        "Trial result → %s conf=%.2f (layer=%s)",
                        label, conf,
                        processor.current_trial.get("layer", "?"),
                    )
                else:
                    logger.info("Trial result: rest (low confidence)")
                # Reset for next trial
                processor.current_trial = None
                processor.trial_baseline = []
                processor.trial_task = []
                processor.trial_baseline_done = False
                processor.trial_task_done = False
                processor.trial_result = None

            # Receive game events
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=0.005)
                event = json.loads(raw)
                processor.handle_game_event(event)
            except (asyncio.TimeoutError, json.JSONDecodeError):
                pass

            await asyncio.sleep(0.02)

    except websockets.exceptions.ConnectionClosed:
        logger.info("Game disconnected: %s:%s", *peer)


# ── CLI ──


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MetaBCI Online MI Inference Server",
    )
    p.add_argument(
        "--host", default=config.HOST,
        help=f"WebSocket host (default: {config.HOST})",
    )
    p.add_argument(
        "--port", type=int, default=config.PORT,
        help=f"WebSocket port (default: {config.PORT})",
    )
    p.add_argument(
        "--stream", default=config.EEG_STREAM_NAME,
        help=f"LSL stream name (default: {config.EEG_STREAM_NAME})",
    )
    p.add_argument(
        "--model", default=str(config.MODEL_DIR / config.MODEL_FILE),
        help="Path to trained model JSON",
    )
    p.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Override stream name
    config.EEG_STREAM_NAME = args.stream

    processor = OnlineMIProcessor()
    processor.load_model(args.model)

    logger.info("=" * 50)
    logger.info("MetaBCI Online MI Bridge")
    logger.info("WebSocket: ws://%s:%d", args.host, args.port)
    logger.info("LSL stream: %s", args.stream)
    logger.info(
        "Classifier: %s",
        "Trained LDA" if processor.classifier and processor.classifier._trained
        else "Threshold fallback",
    )
    logger.info("=" * 50)

    async with websockets.serve(
        lambda ws: handle_connection(ws, processor),
        args.host, args.port,
        max_size=2 ** 20,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
