import os
import time
import math
import magic
from collections import Counter
import numpy as np
from sklearn.cluster import DBSCAN

class SplitFileDetector:
    def __init__(
        self,
        size_tol=0.02,
        entropy_tol=0.1,
        time_window=15,
        min_cluster=3
    ):
        self.size_tol = size_tol
        self.entropy_tol = entropy_tol
        self.time_window = time_window
        self.min_cluster = min_cluster

    # ---------- Low-level features ----------

    def _entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        c = Counter(data)
        total = len(data)
        return -sum((n/total) * math.log2(n/total) for n in c.values())

    def _file_features(self, path):
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)

        with open(path, "rb") as f:
            sample = f.read(100_000)

        entropy = self._entropy(sample)
        mime = magic.from_buffer(sample, mime=True)

        return {
            "path": path,
            "size": size,
            "mtime": mtime,
            "entropy": entropy,
            "mime": mime
        }

    # ---------- Core detection ----------

    def analyze(self, files):
        feats = [self._file_features(f) for f in files]

        sizes = np.array([f["size"] for f in feats]).reshape(-1, 1)
        times = np.array([f["mtime"] for f in feats]).reshape(-1, 1)
        entrs = np.array([f["entropy"] for f in feats]).reshape(-1, 1)

        # Normalisation
        X = np.hstack([
            sizes / sizes.max(),
            (times - times.min()) / max(1, times.max() - times.min()),
            entrs / entrs.max()
        ])

        # Clustering temporel + taille + entropie
        clustering = DBSCAN(
            eps=0.15,
            min_samples=self.min_cluster
        ).fit(X)

        clusters = {}
        for idx, label in enumerate(clustering.labels_):
            if label == -1:
                continue
            clusters.setdefault(label, []).append(feats[idx])

        results = []
        for label, group in clusters.items():
            results.append(self._score_cluster(group))

        return results

    # ---------- Scoring ----------

    def _score_cluster(self, group):
        sizes = [g["size"] for g in group]
        entrs = [g["entropy"] for g in group]
        times = [g["mtime"] for g in group]

        size_score = 1 - (max(sizes) - min(sizes)) / max(sizes)
        entr_score = 1 - (max(entrs) - min(entrs))
        time_score = 1 if max(times) - min(times) < self.time_window else 0

        mime_score = len(set(g["mime"] for g in group)) == 1

        score = (
            0.35 * size_score +
            0.35 * entr_score +
            0.2 * time_score +
            0.1 * int(mime_score)
        )

        return {
            "files": [g["path"] for g in group],
            "score": round(score, 3),
            "count": len(group),
            "suspect": score > 0.7
        }
