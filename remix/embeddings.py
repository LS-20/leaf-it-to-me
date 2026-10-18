"""Load Epicure ingredient embeddings (Radzikowski & Chen, KAIKAKU.AI, CC-BY-4.0).

We load the published safetensors file directly instead of running the repo's
loader code, so the only thing we depend on is the 1,790 x 300 matrix.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

ROOT = Path(__file__).resolve().parent.parent
MODES = ("core", "cooc", "chem")


class Epicure:
    def __init__(self, mode: str = "core"):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        d = ROOT / "models" / f"epicure-{mode}"
        E = load_file(d / "embeddings.safetensors")["embeddings"].astype(np.float32)
        # Config says: raw skip-gram outputs, L2-normalise before cosine ops.
        self.E = E / np.linalg.norm(E, axis=1, keepdims=True)
        itos = json.loads((d / "itos.json").read_text())
        self.names = [itos[str(i)] for i in range(len(itos))]
        self.index = {n: i for i, n in enumerate(self.names)}
        poles = json.loads((d / "supervised_poles.json").read_text())
        self.cuisines = {
            k.split(":", 1)[1]: self._unit(np.array(v, dtype=np.float32))
            for k, v in poles.items()
            if k.startswith("cuisine:")
        }
        self.mode = mode

    @staticmethod
    def _unit(v):
        n = np.linalg.norm(v)
        return v / n if n else v

    def __contains__(self, name):
        return name in self.index

    def vec(self, name):
        return self.E[self.index[name]]

    def centroid(self, names):
        """Mean direction of a set of ingredients (the dish 'context')."""
        ids = [self.index[n] for n in names if n in self.index]
        if not ids:
            return None
        return self._unit(self.E[ids].mean(axis=0))

    def sim(self, a, b_vec):
        return float(self.vec(a) @ b_vec)

    def neighbors(self, name, k=10):
        s = self.E @ self.vec(name)
        order = np.argsort(-s)
        return [(self.names[j], float(s[j])) for j in order if self.names[j] != name][:k]

    def detect_cuisine(self, names):
        """Rank the 7 cuisine poles by cosine with the dish centroid."""
        c = self.centroid(names)
        if c is None:
            return []
        scores = {k: float(v @ c) for k, v in self.cuisines.items()}
        return sorted(scores.items(), key=lambda kv: -kv[1])


@lru_cache(maxsize=None)
def load(mode: str = "core") -> Epicure:
    return Epicure(mode)
