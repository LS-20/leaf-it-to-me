"""Download the three Epicure models (CC-BY-4.0, Radzikowski & Chen, KAIKAKU.AI)."""
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent.parent
FILES = ["embeddings.safetensors", "itos.json", "vocab.json", "config.json",
         "LICENSE", "README.md", "supervised_poles.json", "cuisine_pole_provenance.json"]

for mode in ("core", "cooc", "chem"):
    p = snapshot_download(f"Kaikaku/epicure-{mode}", local_dir=ROOT / "models" / f"epicure-{mode}",
                          allow_patterns=FILES)
    print("downloaded", p)
