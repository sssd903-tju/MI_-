"""Data cleaning / preprocessing for EEG signals.

Uses scipy + numpy for fast filtering.
No heavy deps (mne) in the online path — keeps latency low.
"""

import numpy as np
from scipy import signal
from metabci.brainda.algorithms.feature_analysis import FrequencyAnalysis

from . import config


class Preprocessor:
    """EEG data cleaning: filter → detrend → reject artifacts."""

    def __init__(self, fs: float = config.FS):
        self.fs = fs
        self._notch_b: np.ndarray | None = None
        self._notch_a: np.ndarray | None = None
        self._bandpass_b: np.ndarray | None = None
        self._bandpass_a: np.ndarray | None = None
        self._init_filters()

    def _init_filters(self) -> None:
        """Precompute IIR filter coefficients."""
        nyq = self.fs / 2.0
        # Notch at 50Hz
        self._notch_b, self._notch_a = signal.iirnotch(
            config.NOTCH_FREQ, 30.0, self.fs
        )
        # Bandpass 8-30 Hz (4th order Butterworth)
        self._bandpass_b, self._bandpass_a = signal.butter(
            4,
            [config.BANDPASS_LOW / nyq, config.BANDPASS_HIGH / nyq],
            btype="band",
        )

    # ── full offline pipeline ──

    def clean(self, data: np.ndarray) -> np.ndarray:
        """Full clean: notch → bandpass → detrend per channel.

        Args:
            data: shape (n_samples,) or (n_channels, n_samples)

        Returns:
            cleaned array, same shape as input
        """
        if data.ndim == 1:
            return self._clean_1d(data)
        cleaned = np.zeros_like(data)
        for ch in range(data.shape[0]):
            cleaned[ch] = self._clean_1d(data[ch])
        return cleaned

    def _clean_1d(self, x: np.ndarray) -> np.ndarray:
        """Clean a single channel."""
        # Notch
        x = signal.filtfilt(self._notch_b, self._notch_a, x)
        # Bandpass
        x = signal.filtfilt(self._bandpass_b, self._bandpass_a, x)
        # Linear detrend
        x = signal.detrend(x)
        return x

    # ── fast online path (causal, no filtfilt) ──

    def clean_online(self, data: np.ndarray) -> np.ndarray:
        """Fast online clean: lfilter (causal) → detrend.

        Uses lfilter instead of filtfilt to avoid future-looking.
        Slightly less clean but adds zero latency.

        Args:
            data: shape (n_channels, n_samples)

        Returns:
            cleaned array, same shape
        """
        cleaned = np.zeros_like(data)
        for ch in range(data.shape[0]):
            x = data[ch].copy()
            # Causal notch
            x = signal.lfilter(self._notch_b, self._notch_a, x)
            # Causal bandpass
            x = signal.lfilter(self._bandpass_b, self._bandpass_a, x)
            # Detrend
            cleaned[ch] = signal.detrend(x)
        return cleaned

    # ── bad-channel detection ──

    def detect_bad_channels(
        self, data: np.ndarray, threshold: float = 5.0
    ) -> list[int]:
        """Detect bad channels by amplitude variance outlier.

        Args:
            data: shape (n_channels, n_samples)
            threshold: std multiplier for outlier detection

        Returns:
            list of bad channel indices
        """
        n_ch = data.shape[0]
        stds = np.array([np.std(data[ch]) for ch in range(n_ch)])
        median_std = np.median(stds)
        mad = np.median(np.abs(stds - median_std))
        bad = []
        for ch in range(n_ch):
            z = 0.6745 * (stds[ch] - median_std) / (mad + 1e-10)
            if abs(z) > threshold:
                bad.append(ch)
        return bad

    def interpolate_bad_channels(
        self, data: np.ndarray, bad_indices: list[int]
    ) -> np.ndarray:
        """Simple mean-of-neighbors interpolation for bad channels."""
        if not bad_indices:
            return data
        n_ch = data.shape[0]
        result = data.copy()
        for ch in bad_indices:
            neighbors = []
            if ch > 0 and ch - 1 not in bad_indices:
                neighbors.append(ch - 1)
            if ch < n_ch - 1 and ch + 1 not in bad_indices:
                neighbors.append(ch + 1)
            if neighbors:
                result[ch] = np.mean(data[neighbors], axis=0)
            else:
                result[ch] = np.zeros_like(data[ch])
        return result
