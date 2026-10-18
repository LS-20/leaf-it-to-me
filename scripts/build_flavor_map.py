"""Precompute the 2D flavor map (t-SNE of Epicure-Core embeddings, cosine metric).

Writes data/flavor_map.json. t-SNE keeps neighbors close but distorts long
distances, so the map is for intuition; the swap scores use real cosine similarity.
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.manifold import TSNE

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix.embeddings import load  # noqa: E402

e = load("core")
XY = TSNE(2, perplexity=40, init="pca", metric="cosine", random_state=0).fit_transform(e.E)
XY = (XY - XY.min(0)) / (XY.max(0) - XY.min(0))  # scale to 0..1

# Region labels sit at the median position of a few well-known anchor ingredients.
# (Labels only, for orientation; points are not classified.)
ANCHORS = {
    "East Asian": ["soy_sauce", "miso", "tofu", "doubanjiang", "kimchi", "sesame_oil"],
    "Southeast Asian": ["fish_sauce", "lemongrass", "galangal", "thai_basil", "coconut_milk"],
    "South Asian": ["garam_masala", "paneer", "chana_dal", "fenugreek_leaf", "ghee", "amchur"],
    "Mediterranean": ["olive_oil", "feta_cheese", "oregano", "pasta", "parmesan_cheese"],
    "Latin American": ["tortilla", "salsa", "jalapeno", "enchilada_sauce", "pinto_bean"],
    "Eastern European": ["sauerkraut", "dill", "beet", "rye_bread", "kielbasa"],
    "Baking & sweets": ["vanilla", "flour", "baking_powder", "brown_sugar", "chocolate"],
}
regions = []
for name, anchors in ANCHORS.items():
    ids = [e.index[a] for a in anchors if a in e.index]
    if len(ids) >= 3:
        regions.append({"name": name, "x": round(float(np.median(XY[ids, 0])), 3),
                        "y": round(float(np.median(XY[ids, 1])), 3)})
points = [{"n": n, "x": round(float(XY[i, 0]), 4), "y": round(float(XY[i, 1]), 4)}
          for i, n in enumerate(e.names)]
out = {"regions": regions, "points": points}
(ROOT / "data" / "flavor_map.json").write_text(json.dumps(out, separators=(",", ":")))
print(len(points), "points;", regions)
