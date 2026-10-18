"""Per-ingredient and per-recipe environmental footprint.

Data: Poore & Nemecek (2018), Science 360:987, via Our World in Data (CC-BY-4.0).
Values are global averages per kg of product, farm to retail (median year 2010).
Recipe footprint F = sum_i (grams_i / 1000) * f_i.
"""
import csv
from functools import lru_cache
from pathlib import Path

from .catalog import COMMODITY

DATA = Path(__file__).resolve().parent.parent / "data" / "owid_poore_nemecek.csv"
METRICS = ("ghg", "land", "water")


@lru_cache(maxsize=None)
def table():
    out = {}
    with open(DATA, newline="") as f:
        for row in csv.DictReader(f):
            out[row["commodity"]] = {
                "ghg": float(row["ghg_kgco2e_per_kg"]),
                "land": float(row["land_m2_per_kg"]),
                "water": float(row["water_l_per_kg"]),
            }
    return out


def per_kg(name: str):
    """Return {ghg, land, water, commodity, proxy} or None if unknown."""
    if name not in COMMODITY:
        return None
    commodity, proxy = COMMODITY[name]
    vals = table().get(commodity)
    if vals is None:
        return None
    return {**vals, "commodity": commodity, "proxy": proxy}


def recipe_footprint(items):
    """items: [{epicure, grams}] -> totals plus mass coverage."""
    totals = dict.fromkeys(METRICS, 0.0)
    known_g = total_g = 0.0
    for it in items:
        g = it.get("grams") or 0.0
        total_g += g
        f = per_kg(it["epicure"]) if it.get("epicure") else None
        if f:
            known_g += g
            for m in METRICS:
                totals[m] += g / 1000 * f[m]
    totals["coverage"] = known_g / total_g if total_g else 0.0
    return totals
