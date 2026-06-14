#!/usr/bin/env python3
"""Offline training CLI.

Usage:
    # Train from raw EEG + session JSONL
    python -m metabci_bridge.main_offline \\
        --eeg data/subject01_raw.npy \\
        --session data/session_20260601_120000.jsonl \\
        --onset 2.0 --window 4.0

    # Train with CSP features
    python -m metabci_bridge.main_offline \\
        --eeg data/subject01_raw.fif \\
        --session data/session.jsonl \\
        --csp
"""

import argparse
import json
import logging

from . import config
from .offline_train import OfflineTrainer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MetaBCI Offline MI Training Pipeline",
    )
    p.add_argument(
        "--eeg", required=True,
        help="Path to raw EEG file (.npy, .mat, .fif)",
    )
    p.add_argument(
        "--session", required=True,
        help="Path to session JSONL file with trial timestamps",
    )
    p.add_argument(
        "--onset", type=float, default=config.MI_ONSET_S,
        help=f"Seconds after trial_start to begin window (default: {config.MI_ONSET_S})",
    )
    p.add_argument(
        "--window", type=float, default=config.MI_WINDOW_S,
        help=f"MI window duration in seconds (default: {config.MI_WINDOW_S})",
    )
    p.add_argument(
        "--fs", type=float, default=config.FS,
        help=f"Sampling rate (default: {config.FS})",
    )
    p.add_argument(
        "--output", default=None,
        help="Output model path (default: models/mi_model.json)",
    )
    p.add_argument(
        "--csp", action="store_true",
        help="Also train CSP spatial filters",
    )
    p.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    trainer = OfflineTrainer(fs=args.fs)

    # Run pipeline
    result = trainer.run(
        eeg_path=args.eeg,
        session_path=args.session,
        onset_s=args.onset,
        window_s=args.window,
    )

    # Also train CSP if requested
    if args.csp and trainer._features is not None:
        logger.info("Training CSP filters...")
        windows, labels, _ = trainer.slice_trials(
            None, trainer._trials, args.onset, args.window,
        )
        # Get cleaned data for CSP
        cleaned = trainer.preprocessor.clean(
            trainer.load_eeg(args.eeg)
        )
        windows, labels, _ = trainer.slice_trials(
            cleaned, trainer._trials, args.onset, args.window,
        )

        # Separate classes for CSP (left=1 vs right=2)
        c1_windows = windows[labels == 1]
        c2_windows = windows[labels == 2]
        if len(c1_windows) > 0 and len(c2_windows) > 0:
            trainer.extractor.fit_csp(c1_windows, c2_windows)
            # Save CSP filters
            import numpy as np
            csp_path = config.MODEL_DIR / "csp_filters.npy"
            csp_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(csp_path, trainer.extractor._csp_filters)
            logger.info("CSP filters saved: %s", csp_path)

    # Print results
    print()
    print("=" * 60)
    print("Training Complete")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Model: {config.MODEL_DIR / config.MODEL_FILE}")
    print(f"Meta:  {config.MODEL_DIR / 'mi_model.meta.json'}")


if __name__ == "__main__":
    main()
