#!/usr/bin/env python3
"""Offline MI training with ERD/ERS features.

Flow:
  1. Load BDF + session JSONL
  2. Time-align using meas_date (auto-corrects Beijing→UTC -8h)
  3. For each trial:
     - Baseline: [trial_start, trial_start + 2s]
     - Task:     [trial_start + 2s, trial_start + 6s]
  4. Compute ERD% = (task_power - baseline_power) / baseline_power
  5. Features: ERD per channel × frequency bands (broadband, alpha, beta)
  6. Train LDA classifier
  7. Evaluate & save model

Usage:
    python run_training.py
    python run_training.py --bdf /path/to/data.bdf --session /path/to/session.jsonl
"""

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import mne
from scipy import signal as sig

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.metabci_bridge.classifier import MIClassifier
from python.metabci_bridge import config

FS = 250.0
ONSET_S = 2.0   # baseline duration (trial_start → trial_start+2s)
WINDOW_S = 4.0  # task duration (trial_start+2s → trial_start+6s)
T7_IDX = 4      # BDF channel order: T7
T8_IDX = 5      # BDF channel order: T8

# ── helpers ──

def band_power(x: np.ndarray, fs: float, low: float, high: float) -> float:
    """Power in frequency band [low, high] via Welch PSD."""
    nperseg = min(256, len(x) // 2)
    if nperseg < 32:
        nperseg = len(x) // 4
    f, p = sig.welch(x, fs, nperseg=nperseg)
    mask = (f >= low) & (f <= high)
    if mask.sum() < 2:
        return 0.0
    return float(np.trapezoid(p[mask], f[mask]))


def load_files(bdf_path: Path, session_path: Path) -> tuple:
    """Load BDF data and session JSONL trials."""
    print(f"BDF:     {bdf_path.name}")
    raw = mne.io.read_raw_bdf(str(bdf_path), preload=True)
    data = raw.get_data()
    ch_names = raw.ch_names
    print(f"  Channels: {ch_names}")
    print(f"  Duration: {data.shape[1] / raw.info['sfreq']:.1f}s @ {raw.info['sfreq']}Hz")

    # Time alignment: BDF meas_date is local time (Beijing), stored as UTC → -8h
    meas_date = raw.info.get("meas_date")
    if meas_date.tzinfo is not None:
        bdf_utc = meas_date - timedelta(hours=8)
    else:
        bdf_utc = meas_date
    bdf_start_ms = int(bdf_utc.timestamp() * 1000)

    print(f"Session: {session_path.name}")
    with open(session_path) as f:
        all_lines = [json.loads(l) for l in f if l.strip()]
    trials = [l for l in all_lines if l.get("type") == "trial"]
    gts = [t["ground_truth"] for t in trials]
    print(f"  Trials: {len(trials)} (left={gts.count('left')} right={gts.count('right')})")

    # Verify time alignment
    session_start = next((l for l in all_lines if l["type"] == "session_start"), None)
    if session_start:
        offset_s = (session_start["timestamp_ms"] - bdf_start_ms) / 1000.0
        print(f"  Session offset from BDF start: {offset_s:.1f}s")
        if abs(offset_s) > 60:
            print(f"  ⚠️  Offset >60s — timezone may be wrong. "
                  f"BDF start={bdf_utc}, session={session_start['timestamp_ms']}")

    return raw, data, ch_names, bdf_start_ms, trials


def slice_trial(data: np.ndarray, trial: dict, bdf_start_ms: int) -> tuple | None:
    """Slice baseline and task windows for one trial."""
    t_ms = trial["timestamp_trial_start_ms"]
    t_s = (t_ms - bdf_start_ms) / 1000.0

    bl_onset = int(t_s * FS)
    bl_end = int((t_s + ONSET_S) * FS)
    tk_onset = bl_end
    tk_end = int((t_s + ONSET_S + WINDOW_S) * FS)

    if bl_onset < 0 or tk_end > data.shape[1]:
        return None

    bl = data[:, bl_onset:bl_end]
    tk = data[:, tk_onset:tk_end]
    return bl, tk


def extract_erd_features(bl: np.ndarray, tk: np.ndarray) -> np.ndarray:
    """Extract ERD/ERS features from baseline and task windows.

    ERD% = (task - baseline) / baseline  (negative = ERD, positive = ERS)

    Returns 9 features:
      [ERD_T7, ERD_T8, lateralization,
       ERD_alpha_T7, ERD_alpha_T8, lateral_alpha,
       ERD_beta_T7, ERD_beta_T8, lateral_beta]
    """
    t7_bl = bl[T7_IDX] - bl[T7_IDX].mean()
    t8_bl = bl[T8_IDX] - bl[T8_IDX].mean()
    t7_tk = tk[T7_IDX] - tk[T7_IDX].mean()
    t8_tk = tk[T8_IDX] - tk[T8_IDX].mean()

    # Broadband (0.5-30Hz)
    bp_bl_t7 = band_power(t7_bl, FS, 0.5, 30)
    bp_bl_t8 = band_power(t8_bl, FS, 0.5, 30)
    bp_tk_t7 = band_power(t7_tk, FS, 0.5, 30)
    bp_tk_t8 = band_power(t8_tk, FS, 0.5, 30)

    erd_t7 = (bp_tk_t7 - bp_bl_t7) / (bp_bl_t7 + 1e-15)
    erd_t8 = (bp_tk_t8 - bp_bl_t8) / (bp_bl_t8 + 1e-15)
    lateral = erd_t7 - erd_t8

    # Alpha (8-13Hz)
    a_bl_t7 = band_power(t7_bl, FS, 8, 13)
    a_bl_t8 = band_power(t8_bl, FS, 8, 13)
    a_tk_t7 = band_power(t7_tk, FS, 8, 13)
    a_tk_t8 = band_power(t8_tk, FS, 8, 13)

    erd_a_t7 = (a_tk_t7 - a_bl_t7) / (a_bl_t7 + 1e-15)
    erd_a_t8 = (a_tk_t8 - a_bl_t8) / (a_bl_t8 + 1e-15)
    lateral_a = erd_a_t7 - erd_a_t8

    # Beta (13-30Hz)
    b_bl_t7 = band_power(t7_bl, FS, 13, 30)
    b_bl_t8 = band_power(t8_bl, FS, 13, 30)
    b_tk_t7 = band_power(t7_tk, FS, 13, 30)
    b_tk_t8 = band_power(t8_tk, FS, 13, 30)

    erd_b_t7 = (b_tk_t7 - b_bl_t7) / (b_bl_t7 + 1e-15)
    erd_b_t8 = (b_tk_t8 - b_bl_t8) / (b_bl_t8 + 1e-15)
    lateral_b = erd_b_t7 - erd_b_t8

    return np.array([
        erd_t7, erd_t8, lateral,
        erd_a_t7, erd_a_t8, lateral_a,
        erd_b_t7, erd_b_t8, lateral_b,
    ])


FEATURE_NAMES = [
    "ERD_T7", "ERD_T8", "lateral",
    "ERD_alpha_T7", "ERD_alpha_T8", "lateral_alpha",
    "ERD_beta_T7", "ERD_beta_T8", "lateral_beta",
]


# ── main ──

def main():
    p = argparse.ArgumentParser(description="Offline MI training with ERD/ERS")
    p.add_argument("--bdf", default=str(
        Path.home() / "Downloads" / "测试数据3.bdf"))
    p.add_argument("--session", default=str(
        Path.home() / "Library/Application Support/Godot/app_userdata/"
        "跳一跳/training_data/session_20260609_223707.jsonl"))
    p.add_argument("--output", default=None)
    args = p.parse_args()

    bdf_path = Path(args.bdf)
    session_path = Path(args.session)
    print("=" * 60)

    # Load
    raw, data, ch_names, bdf_start_ms, trials = load_files(bdf_path, session_path)

    # Slice + extract features
    feats, labels_list, trial_info = [], [], []
    print(f"\n{'Trial':<7} {'GT':<7} {'ERD_T7%':>8} {'ERD_T8%':>8} "
          f"{'lateral':>10} {'pred_simple':<8}")
    print("-" * 65)

    for trial in trials:
        gt = trial["ground_truth"]
        windows = slice_trial(data, trial, bdf_start_ms)
        if windows is None:
            print(f"  SKIP trial {trial['trial_id']}: out of range")
            continue

        bl, tk = windows
        f = extract_erd_features(bl, tk)
        feats.append(f)
        labels_list.append(1 if gt == "left" else 2)

        simple = "left" if f[2] > 0 else "right"
        ok = "✓" if simple == gt else ""
        print(f"Trial {trial['trial_id']:<2} {gt:<7} {f[0]*100:>+7.1f}% "
              f"{f[1]*100:>+7.1f}% {f[2]:>+10.4f} {simple:<8} {ok}")

    X = np.array(feats)
    y = np.array(labels_list)
    print(f"\nTotal: {len(X)} trials × {X.shape[1]} features")

    # Train
    print("\n--- Training LDA ---")
    clf = MIClassifier()
    clf.fit(X, y)
    y_pred = clf.predict(X)
    acc = np.mean(y_pred == y)
    print(f"Accuracy: {acc:.1%}")

    for label in [1, 2]:
        m = y == label
        n, correct = m.sum(), (y_pred[m] == label).sum()
        name = config.LABEL_MAP[label]
        print(f"  {name}: {correct}/{n} ({correct/n:.1%})" if n > 0
              else f"  {name}: 0")

    # Feature importance
    print(f"\nWeights (neg→left, pos→right):")
    for name, w in zip(FEATURE_NAMES, clf._w):
        direction = "→ LEFT" if w < 0 else "→ RIGHT"
        bar = "█" * min(40, int(abs(w) * 20)) if abs(w) > 0.05 else ""
        print(f"  {name:<16} {w:>+10.4f} {direction}  {bar}")

    # Decision scores
    print(f"\nDecision:")
    for i in range(len(X)):
        s = float(clf.decision_function(X[i]))
        gt_name = "left" if y[i] == 1 else "right"
        pred_name = config.LABEL_MAP[y_pred[i]]
        ok = "✓" if y_pred[i] == y[i] else "✗"
        print(f"  T{i+1} {gt_name:<6}: score={s:+.4f} → {pred_name} {ok}")

    # Save
    model_path = Path(args.output) if args.output else (
        config.MODEL_DIR / config.MODEL_FILE)
    clf.save(model_path)

    meta = {
        "fs": FS, "onset_s": ONSET_S, "window_s": WINDOW_S,
        "n_trials": len(X), "accuracy": round(float(acc), 3),
        "channels": ch_names,
        "used_channels": ["T7", "T8"],
        "t7_idx": T7_IDX, "t8_idx": T8_IDX,
        "method": "ERD/ERS — (task−baseline)/baseline",
        "feature_names": FEATURE_NAMES,
        "note": "No bandpass filter; broadband + alpha + beta ERD",
    }
    meta_path = model_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"\nModel: {model_path}")
    print(f"Meta:  {meta_path}")
    print("=" * 60)
    print("DONE")


if __name__ == "__main__":
    main()
