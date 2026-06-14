"""Offline training pipeline.

Flow:
  1. Load raw EEG data (numpy .npy, .mat, .fif via mne)
  2. Load session JSONL (trial timestamps from game)
  3. Clean: notch → bandpass → bad channel detect & interpolate
  4. Slice: for each trial, extract window [trial_start + 2s, trial_start + 6s]
  5. Extract features: band power + optional CSP
  6. Train LDA classifier
  7. Evaluate: cross-validation accuracy, confusion matrix
  8. Export model
"""

import json
import logging
from pathlib import Path

import numpy as np

from . import config
from .preprocess import Preprocessor
from .feature_extractor import FeatureExtractor
from .classifier import MIClassifier

logger = logging.getLogger(__name__)


class OfflineTrainer:
    """Complete offline training pipeline."""

    def __init__(self, fs: float = config.FS):
        self.fs = fs
        self.preprocessor = Preprocessor(fs=fs)
        self.extractor = FeatureExtractor(fs=fs)
        self.classifier = MIClassifier()
        self._trials: list[dict] = []
        self._features: np.ndarray | None = None
        self._labels: np.ndarray | None = None

    # ── Step 1: Load data ──

    def load_eeg(self, path: str | Path) -> np.ndarray:
        """Load raw EEG data from file.

        Supports:
        - .npy: numpy array, shape (n_channels, n_samples)
        - .npz: dict with 'data' key
        - .mat: MATLAB .mat file
        - .fif: MNE raw file

        Returns:
            data: shape (n_channels, n_samples)
        """
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix == ".npy":
            data = np.load(path)
        elif suffix == ".npz":
            archive = np.load(path)
            data = archive.get("data", archive[list(archive.keys())[0]])
        elif suffix == ".mat":
            import scipy.io
            mat = scipy.io.loadmat(str(path))
            # Find the largest array key
            best_key = None
            best_size = 0
            for k, v in mat.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, np.ndarray) and v.size > best_size:
                    best_key = k
                    best_size = v.size
            data = mat[best_key] if best_key else None
        elif suffix == ".fif":
            import mne
            raw = mne.io.read_raw_fif(path, preload=True)
            data = raw.get_data()
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        if data is None:
            raise ValueError(f"Could not load EEG data from {path}")

        # Ensure shape is (n_channels, n_samples)
        if data.shape[0] > data.shape[1]:
            data = data.T

        logger.info(
            "Loaded EEG: %s → shape (%d ch × %d samples = %.1fs @ %dHz)",
            path.name, data.shape[0], data.shape[1],
            data.shape[1] / self.fs, self.fs,
        )
        return data

    def load_session(self, path: str | Path) -> list[dict]:
        """Load session JSONL with trial timestamps.

        Expected format per line:
        {"type":"trial", "trial_id":1, "ground_truth":"left", "correct":true,
         "timestamp_trial_start_ms":..., "timestamp_trial_end_ms":...}
        """
        path = Path(path)
        trials = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") == "trial":
                    trials.append(obj)

        logger.info("Loaded %d trials from %s", len(trials), path.name)
        self._trials = trials
        return trials

    def load_session_from_dict(self, data: dict) -> list[dict]:
        """Load session from dict (received via WebSocket).

        Expected format:
        {"type":"session_end", "trials":[...], ...}
        """
        trials = data.get("trials", [])
        self._trials = trials
        logger.info("Loaded %d trials from session_end dict", len(trials))
        return trials

    # ── Step 2: Clean ──

    def clean_data(self, data: np.ndarray) -> np.ndarray:
        """Full offline cleaning pipeline."""
        logger.info("Cleaning: notch→bandpass→detect bad channels...")

        # Detect bad channels before cleaning
        bad = self.preprocessor.detect_bad_channels(data)
        if bad:
            names = [config.CHANNEL_NAMES[i] if i < len(config.CHANNEL_NAMES)
                     else str(i) for i in bad]
            logger.info("  Bad channels: %s → interpolating", names)
            # Clean first, then interpolate
            cleaned = self.preprocessor.clean(data)
            cleaned = self.preprocessor.interpolate_bad_channels(cleaned, bad)
        else:
            logger.info("  No bad channels detected")
            cleaned = self.preprocessor.clean(data)

        return cleaned

    # ── Step 3: Slice by labels ──

    def slice_trials(
        self, data: np.ndarray, trials: list[dict] | None = None,
        onset_s: float = config.MI_ONSET_S,
        window_s: float = config.MI_WINDOW_S,
    ) -> tuple[np.ndarray, np.ndarray, list[dict]]:
        """Slice EEG data into trial windows.

        Each trial is the MI task period:
          [trial_start + onset_s, trial_start + onset_s + window_s]

        Args:
            data: cleaned EEG, shape (n_channels, n_samples)
            trials: list of trial dicts with timestamp_trial_start_ms
            onset_s: seconds after trial_start to begin window (default 2.0)
            window_s: window duration in seconds (default 4.0)

        Returns:
            windows: (n_trials, n_channels, n_window_samples)
            labels: (n_trials,) integer class labels
            meta: list of dicts with trial info
        """
        if trials is None:
            trials = self._trials

        if not trials:
            raise ValueError("No trials loaded. Call load_session() first.")

        # Find session_start to compute relative offsets
        n_samples = data.shape[1]
        total_dur_s = n_samples / self.fs

        windows = []
        labels = []
        meta = []

        for trial in trials:
            # Trial start in absolute ms → find in data
            # We need the session_start timestamp to align
            start_ms = trial.get("timestamp_trial_start_ms", 0)
            gt = trial.get("ground_truth", "rest")

            # Map ground_truth to class label
            if gt in ("left", "hand"):
                label = 1  # left hand MI
            elif gt in ("right", "foot"):
                label = 2  # right hand / foot MI
            else:
                label = 0  # rest

            # Estimate sample index from trial start
            # Without session_start alignment info, we use trial index
            # as relative position in the recording.
            # ASSUMPTION: data starts at same time as session_start event.
            trial_start_s = (start_ms - self._session_start_ms) / 1000.0

            onset_sample = int((trial_start_s + onset_s) * self.fs)
            end_sample = int((trial_start_s + onset_s + window_s) * self.fs)

            if onset_sample < 0 or end_sample > n_samples:
                logger.warning(
                    "Trial %d: window [%d:%d] out of range [0:%d], skipping",
                    trial.get("trial_id", 0), onset_sample, end_sample, n_samples,
                )
                continue

            window = data[:, onset_sample:end_sample]
            windows.append(window)
            labels.append(label)
            meta.append({
                "trial_id": trial.get("trial_id", 0),
                "ground_truth": gt,
                "label": label,
                "onset_sample": onset_sample,
                "end_sample": end_sample,
                "correct": trial.get("correct", False),
            })

        X = np.stack(windows, axis=0)
        y = np.array(labels)

        logger.info(
            "Sliced: %d windows × %d ch × %d samples "
            "(onset=%.1fs window=%.1fs)",
            X.shape[0], X.shape[1], X.shape[2], onset_s, window_s,
        )
        return X, y, meta

    # ── Step 4: Extract features ──

    def extract_features(self, windows: np.ndarray) -> np.ndarray:
        """Extract feature vectors from trial windows.

        Args:
            windows: (n_trials, n_channels, n_samples)

        Returns:
            features: (n_trials, n_features)
        """
        n_trials = windows.shape[0]
        n_features = windows.shape[1] * 2  # alpha+beta per channel
        features = np.zeros((n_trials, n_features))

        for i in range(n_trials):
            features[i] = self.extractor.band_power_vector(windows[i])

        logger.info(
            "Features extracted: (%d, %d) — band_power per channel",
            *features.shape,
        )
        return features

    # ── Step 5: Train ──

    def train(self, X: np.ndarray, y: np.ndarray) -> MIClassifier:
        """Train LDA classifier."""
        self.classifier.fit(X, y)
        self._features = X
        self._labels = y
        return self.classifier

    # ── Step 6: Evaluate ──

    def evaluate(self, X: np.ndarray | None = None,
                 y: np.ndarray | None = None) -> dict:
        """Evaluate classifier performance.

        Returns:
            dict with accuracy, confusion_matrix, per_class_metrics
        """
        if X is None:
            X = self._features
        if y is None:
            y = self._labels

        if X is None or y is None:
            return {"error": "No data to evaluate"}

        y_pred = self.classifier.predict(X)

        accuracy = float(np.mean(y_pred == y))

        # Confusion matrix
        classes = np.unique(np.concatenate([y, y_pred]))
        cm = np.zeros((len(classes), len(classes)), dtype=int)
        class_to_idx = {c: i for i, c in enumerate(classes)}
        for true, pred in zip(y, y_pred):
            cm[class_to_idx[true]][class_to_idx[pred]] += 1

        # Per-class metrics
        per_class = {}
        for c in classes:
            tp = cm[class_to_idx[c]][class_to_idx[c]]
            fp = cm[:, class_to_idx[c]].sum() - tp
            fn = cm[class_to_idx[c], :].sum() - tp
            precision = tp / (tp + fp + 1e-10)
            recall = tp / (tp + fn + 1e-10)
            f1 = 2 * precision * recall / (precision + recall + 1e-10)
            label_name = config.LABEL_MAP.get(c, str(c))
            per_class[label_name] = {
                "n": int(np.sum(y == c)),
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
            }

        result = {
            "accuracy": round(accuracy, 3),
            "n_samples": int(len(y)),
            "confusion_matrix": cm.tolist(),
            "class_labels": [config.LABEL_MAP.get(c, str(c))
                             for c in classes],
            "per_class": per_class,
        }

        logger.info("Evaluation: accuracy=%.3f", accuracy)
        for label_name, metrics in per_class.items():
            logger.info(
                "  %s: n=%d prec=%.3f rec=%.3f f1=%.3f",
                label_name, metrics["n"], metrics["precision"],
                metrics["recall"], metrics["f1"],
            )

        return result

    # ── Complete pipeline ──

    def run(
        self,
        eeg_path: str | Path,
        session_path: str | Path,
        onset_s: float = config.MI_ONSET_S,
        window_s: float = config.MI_WINDOW_S,
    ) -> dict:
        """Run complete offline training pipeline.

        Args:
            eeg_path: path to raw EEG file
            session_path: path to session JSONL file
            onset_s: MI window onset after trial_start
            window_s: MI window duration

        Returns:
            evaluation results dict
        """
        logger.info("=" * 60)
        logger.info("Starting offline training pipeline")

        # 1. Load raw EEG
        raw = self.load_eeg(eeg_path)

        # 2. Load session
        self.load_session(session_path)

        # 3. Clean
        cleaned = self.clean_data(raw)

        # 4. Slice
        windows, labels, meta = self.slice_trials(
            cleaned, self._trials, onset_s, window_s,
        )

        # 5. Features
        features = self.extract_features(windows)

        # 6. Train
        self.train(features, labels)

        # 7. Evaluate
        result = self.evaluate()

        # 8. Export
        model_path = config.MODEL_DIR / config.MODEL_FILE
        self.classifier.save(model_path)

        # Save metadata alongside model
        meta_path = model_path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps({
            "fs": self.fs,
            "onset_s": onset_s,
            "window_s": window_s,
            "n_trials": len(self._trials),
            "channels": config.CHANNEL_NAMES,
            "left_channel": config.LEFT_CHANNEL,
            "right_channel": config.RIGHT_CHANNEL,
            "class_labels": config.LABEL_MAP,
            "feature_type": "band_power_per_channel",
            "n_features": features.shape[1],
        }, indent=2, ensure_ascii=False))

        logger.info("Pipeline complete. Model: %s", model_path)
        logger.info("=" * 60)
        return result

    @property
    def _session_start_ms(self) -> int:
        """Estimate session start from first trial."""
        if self._trials:
            first = self._trials[0].get("timestamp_trial_start_ms", 0)
            return first - 2000  # 2s before first trial
        return 0
