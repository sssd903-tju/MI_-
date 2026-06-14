"""Feature extraction for MI classification.

Supported methods:
- band_power: alpha / beta 频段功率比 (fast, online-friendly)
- csp: Common Spatial Patterns (offline, needs training data)

Uses MetaBCI's FrequencyAnalysis where appropriate.
"""

import numpy as np
from scipy import integrate, signal

from . import config


class FeatureExtractor:
    """Extract features from cleaned EEG windows."""

    def __init__(self, fs: float = config.FS):
        self.fs = fs
        self._csp_filters: np.ndarray | None = None
        self._csp_pairs: int = 2  # use top-2 CSP pairs

    # ── Band power features (fast, always available) ──

    def band_power_ratio(
        self, data: np.ndarray, left_idx: int = config.LEFT_IDX,
        right_idx: int = config.RIGHT_IDX
    ) -> dict:
        """Compute band power ratio between left/right channels.

        Args:
            data: shape (n_channels, n_samples)
            left_idx, right_idx: channel indices

        Returns:
            dict with alpha_power, beta_power, ratio, erds
        """
        left = data[left_idx]
        right = data[right_idx]

        # PSD via Welch
        nperseg = min(128, len(left) // 2)
        if nperseg < 32:
            nperseg = len(left) // 4

        f_l, p_l = signal.welch(left, self.fs, nperseg=nperseg)
        f_r, p_r = signal.welch(right, self.fs, nperseg=nperseg)

        # Alpha band (8-13 Hz)
        a_low, a_high = config.ALPHA_BAND
        alpha_l = integrate.trapezoid(
            p_l[(f_l >= a_low) & (f_l <= a_high)],
            f_l[(f_l >= a_low) & (f_l <= a_high)],
        )
        alpha_r = integrate.trapezoid(
            p_r[(f_r >= a_low) & (f_r <= a_high)],
            f_r[(f_r >= a_low) & (f_r <= a_high)],
        )

        # Beta band (13-30 Hz)
        b_low, b_high = config.BETA_BAND
        beta_l = integrate.trapezoid(
            p_l[(f_l >= b_low) & (f_l <= b_high)],
            f_l[(f_l >= b_low) & (f_l <= b_high)],
        )
        beta_r = integrate.trapezoid(
            p_r[(f_r >= b_low) & (f_r <= b_high)],
            f_r[(f_r >= b_low) & (f_r <= b_high)],
        )

        # Total power left/right
        total_l = alpha_l + beta_l
        total_r = alpha_r + beta_r

        # ERDS-like index: (L-R)/(L+R)
        erds = (total_l - total_r) / (total_l + total_r + 1e-10)
        ratio = total_l / (total_r + 1e-10)

        return {
            "alpha_left": float(alpha_l),
            "alpha_right": float(alpha_r),
            "beta_left": float(beta_l),
            "beta_right": float(beta_r),
            "total_left": float(total_l),
            "total_right": float(total_r),
            "erds": float(erds),
            "ratio": float(ratio),
        }

    def band_power_vector(
        self, data: np.ndarray
    ) -> np.ndarray:
        """Full-channel band-power feature vector (for offline training).

        Returns:
            shape (n_channels * 2,) — [alpha_0..alpha_7, beta_0..beta_7]
        """
        n_ch = data.shape[0]
        features = np.zeros(n_ch * 2)

        nperseg = min(128, data.shape[1] // 2)
        if nperseg < 32:
            nperseg = data.shape[1] // 4

        for ch in range(n_ch):
            f, p = signal.welch(data[ch], self.fs, nperseg=nperseg)

            a_low, a_high = config.ALPHA_BAND
            alpha = integrate.trapezoid(
                p[(f >= a_low) & (f <= a_high)],
                f[(f >= a_low) & (f <= a_high)],
            )
            b_low, b_high = config.BETA_BAND
            beta = integrate.trapezoid(
                p[(f >= b_low) & (f <= b_high)],
                f[(f >= b_low) & (f <= b_high)],
            )

            features[ch] = alpha
            features[ch + n_ch] = beta

        return features

    def quick_band_power(
        self, data: np.ndarray
    ) -> tuple[float, float]:
        """Fast 2-channel band power for online classification.

        Uses simple variance-of-diff as proxy for band power
        (same approach as original lsl_bridge_server.py for speed).

        Returns:
            (left_power, right_power)
        """
        left = data[config.LEFT_IDX]
        right = data[config.RIGHT_IDX]

        # Variance of 1st diff ≈ high-pass energy
        if len(left) < 4 or len(right) < 4:
            return 0.0, 0.0

        diff_l = np.diff(left)
        diff_r = np.diff(right)

        return float(np.var(diff_l)), float(np.var(diff_r))

    # ── CSP (offline training) ──

    def fit_csp(
        self, class1_data: np.ndarray, class2_data: np.ndarray
    ) -> np.ndarray:
        """Fit CSP spatial filters.

        Args:
            class1_data: (n_trials, n_channels, n_samples) for class 1
            class2_data: (n_trials, n_channels, n_samples) for class 2

        Returns:
            CSP filter matrix, shape (n_pairs*2, n_channels)
        """
        n_ch = class1_data.shape[1]

        # Compute covariance matrices
        cov1 = np.zeros((n_ch, n_ch))
        for trial in class1_data:
            cov1 += np.cov(trial)
        cov1 /= len(class1_data)

        cov2 = np.zeros((n_ch, n_ch))
        for trial in class2_data:
            cov2 += np.cov(trial)
        cov2 /= len(class2_data)

        # Generalized eigenvalue decomposition
        eigvals, eigvecs = np.linalg.eig(
            np.linalg.solve(cov1, cov1 + cov2)
        )

        # Sort by eigenvalue distance from 0.5
        idx = np.argsort(np.abs(eigvals - 0.5))[::-1]

        # Take top pairs
        n_pairs = min(self._csp_pairs, n_ch // 2)
        selected = []
        for i in range(n_pairs):
            selected.append(eigvecs[:, idx[i]])
            selected.append(eigvecs[:, idx[-(i + 1)]])

        self._csp_filters = np.array(selected)
        return self._csp_filters

    def apply_csp(self, data: np.ndarray) -> np.ndarray:
        """Apply CSP filters to get feature vector.

        Args:
            data: shape (n_channels, n_samples)

        Returns:
            CSP feature vector, shape (n_filters,)
        """
        if self._csp_filters is None:
            raise ValueError("CSP not fitted. Call fit_csp first.")

        # Apply filters
        projected = self._csp_filters @ data  # (n_filters, n_samples)
        # Log-variance features
        features = np.log(np.var(projected, axis=1) + 1e-10)
        return features

    def has_csp(self) -> bool:
        return self._csp_filters is not None
