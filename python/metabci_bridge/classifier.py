"""MI classifier — LDA with optional CSP features.

Priority: LDA (fast, stable, well-suited for small MI datasets).
Can also use SVM via sklearn as optional backend.
"""

import json
import logging
from pathlib import Path

import numpy as np
from scipy import linalg

from . import config

logger = logging.getLogger(__name__)


class MIClassifier:
    """Linear Discriminant Analysis for MI 2-class classification.

    Uses regularized LDA (shrinkage) for robustness with small samples.
    """

    def __init__(self):
        self._w: np.ndarray | None = None  # weight vector
        self._b: float = 0.0              # bias
        self._classes: np.ndarray | None = None
        self._feature_names: list[str] = []
        self._n_features: int = 0
        self._shrinkage: float = 0.1
        self._trained: bool = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> "MIClassifier":
        """Train LDA classifier.

        Args:
            X: (n_samples, n_features)
            y: (n_samples,) integer class labels
            feature_names: optional names for each feature column
        """
        self._classes = np.unique(y)
        if len(self._classes) != 2:
            raise ValueError(
                f"LDA needs exactly 2 classes, got {len(self._classes)}: "
                f"{self._classes.tolist()}"
            )

        self._n_features = X.shape[1]
        if feature_names:
            self._feature_names = feature_names
        else:
            self._feature_names = [f"feat_{i}" for i in range(self._n_features)]

        # Split classes
        c0 = self._classes[0]
        c1 = self._classes[1]
        X0 = X[y == c0]
        X1 = X[y == c1]

        # Class means
        mu0 = np.mean(X0, axis=0)
        mu1 = np.mean(X1, axis=0)

        # Pooled covariance with shrinkage
        cov0 = np.cov(X0, rowvar=False)
        cov1 = np.cov(X1, rowvar=False)
        n0, n1 = len(X0), len(X1)
        pooled = (n0 * cov0 + n1 * cov1) / (n0 + n1)

        # Ledoit-Wolf style shrinkage to identity
        target = np.trace(pooled) / self._n_features * np.eye(self._n_features)
        pooled = (1.0 - self._shrinkage) * pooled + self._shrinkage * target

        # Regularize
        pooled += 1e-6 * np.eye(self._n_features)

        # Fisher LDA
        self._w = linalg.solve(pooled, mu1 - mu0, assume_a="pos")

        # Bias: midpoint
        self._b = -0.5 * (mu0 + mu1).dot(self._w)

        self._trained = True
        logger.info(
            "LDA trained: n_samples=%d n_features=%d "
            "class_balance=%d/%d shrinkage=%.2f",
            len(X), self._n_features, n0, n1, self._shrinkage,
        )
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels.

        Args:
            X: (n_samples, n_features) or (n_features,)

        Returns:
            int array of predicted labels
        """
        scores = self.decision_function(X)
        if scores.ndim == 0:
            return self._classes[0] if scores < 0 else self._classes[1]
        return np.where(scores < 0, self._classes[0], self._classes[1])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Probability estimates via sigmoid of decision score.

        Returns:
            (n_samples, 2) array — [p_class0, p_class1]
        """
        scores = self.decision_function(X)
        single = scores.ndim == 0
        if single:
            scores = np.array([scores])

        # Sigmoid: p = 1 / (1 + exp(-|score|))
        prob_c1 = 1.0 / (1.0 + np.exp(-np.abs(scores)))
        prob_c0 = 1.0 - prob_c1

        # Build output: [p_class0, p_class1]
        prob = np.zeros((len(scores), 2))
        for i, s in enumerate(scores):
            if s >= 0:
                prob[i, 0] = prob_c0[i]
                prob[i, 1] = prob_c1[i]
            else:
                prob[i, 0] = prob_c1[i]
                prob[i, 1] = prob_c0[i]

        return prob[0] if single else prob

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """Raw decision score. >0 → class 1, <0 → class 0."""
        if not self._trained:
            raise RuntimeError("Classifier not trained")
        X = np.atleast_1d(np.asarray(X, dtype=np.float64))
        single = X.ndim == 1
        if single:
            X = X.reshape(1, -1)
        scores = X.dot(self._w) + self._b
        return scores[0] if single else scores

    # ── Serialization ──

    def save(self, path: Path | str) -> None:
        """Save model as JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "w": self._w.tolist() if self._w is not None else [],
            "b": self._b,
            "classes": self._classes.tolist() if self._classes is not None else [],
            "feature_names": self._feature_names,
            "shrinkage": self._shrinkage,
            "n_features": self._n_features,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info("Model saved to %s", path)

    @classmethod
    def load(cls, path: Path | str) -> "MIClassifier":
        """Load model from JSON."""
        path = Path(path)
        data = json.loads(path.read_text())
        obj = cls()
        obj._w = np.array(data["w"]) if data["w"] else None
        obj._b = data["b"]
        obj._classes = np.array(data["classes"]) if data["classes"] else None
        obj._feature_names = data.get("feature_names", [])
        obj._shrinkage = data.get("shrinkage", 0.1)
        obj._n_features = data.get("n_features", 0)
        obj._trained = obj._w is not None and len(obj._w) > 0
        logger.info("Model loaded from %s (trained=%s)", path, obj._trained)
        return obj
