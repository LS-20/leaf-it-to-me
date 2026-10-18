"""Command-line demo.

  python cli.py --sample butter_chicken --mode vegan
  python cli.py --text "1 lb beef, 2 cups rice, ..." --mode vegetarian
  python cli.py --photo recipe.jpg
"""
import argparse
import mimetypes
from pathlib import Path

from remix.adapters import get_ingredients
from remix.samples import SAMPLES
from remix.swap import remix


def show(r):
    b, a = r["footprint_before"], r["footprint_after"]
    print(f"\n=== {r['title']}  |  mode: {r['mode']}  |  model: epicure-{r['model']}")
    if r["cuisine"]:
        print("Detected cuisine: " + ", ".join(f"{k.replace('_', ' ')} ({v:.2f})" for k, v in r["cuisine"]))
    print("\nSwaps (highest impact first):")
    if not r["swaps"]:
        print("  none needed")
    for s in r["swaps"]:
        alt = ", ".join(x["name"] for x in s["alternatives"])
        proxy = " [footprint proxy]" if s.get("proxy") else ""
        print(f"  {s['from']} ({s['grams']:.0f} g) -> {s['to'].replace('_', ' ')}"
              f"   fit {s['fit']:.2f}, cuisine {s['cuisine_fit']:.2f}{proxy}")
        if alt:
            print(f"      also plausible: {alt.replace('_', ' ')}")
    pct = (a["ghg"] - b["ghg"]) / b["ghg"] * 100 if b["ghg"] else 0
    print(f"\nFootprint (whole recipe, Poore & Nemecek global averages):")
    print(f"  CO2e   {b['ghg']:6.2f} kg -> {a['ghg']:6.2f} kg   ({pct:+.0f}%)")
    print(f"  Land   {b['land']:6.1f} m2 -> {a['land']:6.1f} m2")
    print(f"  Water  {b['water']:6.0f} L  -> {a['water']:6.0f} L")
    print(f"  Coverage: {b['coverage']:.0%} of recipe weight has footprint data (before), {a['coverage']:.0%} (after)")
    if r["nutrient_flags"]:
        print("\nNutrition to watch (not medical advice):")
        for n in r["nutrient_flags"]:
            print(f"  {n['nutrient']}: was in {', '.join(n['lost_from'])}. Tip: {n['tip']}")
    if r["warnings"]:
        print("\nWarnings:")
        for w in r["warnings"]:
            print("  " + w)
    print("\nSwaps are plausible pairings from ingredient co-occurrence, not taste-tested.")


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", choices=sorted(SAMPLES))
    g.add_argument("--text")
    g.add_argument("--photo")
    p.add_argument("--mode", default="vegan", choices=["pescetarian", "vegetarian", "vegan"])
    p.add_argument("--model", default="core", choices=["core", "cooc", "chem"])
    p.add_argument("--no-cuisine-lock", action="store_true")
    a = p.parse_args()

    if a.sample:
        recipe = get_ingredients("sample", a.sample)
    elif a.text:
        recipe = get_ingredients("text", a.text)
    else:
        path = Path(a.photo)
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        recipe = get_ingredients("photo", (path.read_bytes(), mime))
    show(remix(recipe, mode=a.mode, model=a.model, cuisine_lock=not a.no_cuisine_lock))


if __name__ == "__main__":
    main()
