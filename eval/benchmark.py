"""Swap benchmark: does the ranker pick the protein a dish's own well-known
plant-based version uses?

Gold answers were written down BEFORE running any method (hand-labelled by us
from common vegetarian versions of each dish). Small N, our own labels: treat
as a sanity check, not a published benchmark.

Run:  python eval/benchmark.py
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from remix import catalog as C  # noqa: E402
from remix.embeddings import load  # noqa: E402
from remix.swap import rank_swaps  # noqa: E402

# (dish, cuisine, meat, other ingredients, gold plant proteins)
DISHES = [
    ("Butter chicken", "South Asian", "chicken", ["garam_masala", "tomato", "cream", "butter", "fenugreek_leaf", "ginger", "garlic", "onion"], ["chickpea", "chana_dal"]),
    ("Chicken tikka masala", "South Asian", "chicken", ["yogurt", "garam_masala", "cumin", "tomato", "coriander", "ginger", "kashmiri_chili"], ["chickpea", "chana_dal"]),
    ("Lamb rogan josh", "South Asian", "lamb", ["yogurt", "kashmiri_chili", "cardamom", "clove", "fennel_seed", "ginger", "onion"], ["chickpea", "chana_dal", "lentil"]),
    ("Keema", "South Asian", "lamb", ["green_pea", "garam_masala", "onion", "tomato", "ginger", "cumin", "turmeric"], ["lentil", "chana_dal", "chickpea"]),
    ("Beef tacos", "Latin American", "beef", ["tortilla", "chili_powder", "cumin", "onion", "lime", "salsa", "cheddar_cheese"], ["pinto_bean", "black_bean"]),
    ("Chili con carne", "Latin American", "beef", ["chili_powder", "cumin", "tomato", "onion", "bell_pepper", "garlic", "oregano"], ["kidney_bean", "black_bean", "pinto_bean"]),
    ("Chicken burrito", "Latin American", "chicken", ["tortilla", "rice", "salsa", "sour_cream", "avocado", "lime", "cumin"], ["black_bean", "pinto_bean"]),
    ("Chicken enchiladas", "Latin American", "chicken", ["enchilada_sauce", "tortilla", "queso_fresco", "onion", "jalapeno", "cumin"], ["black_bean", "pinto_bean"]),
    ("Carnitas", "Latin American", "pork", ["orange", "lime", "cumin", "oregano", "tortilla", "onion", "jalapeno"], ["jackfruit", "pinto_bean", "black_bean"]),
    ("Mapo tofu with pork", "East Asian", "pork", ["tofu", "doubanjiang", "sichuan_peppercorn", "garlic", "ginger", "scallion", "soy_sauce"], ["tofu", "mushroom"]),
    ("Kung pao chicken", "East Asian", "chicken", ["peanut", "soy_sauce", "sichuan_peppercorn", "rice_vinegar", "scallion", "garlic", "ginger"], ["tofu"]),
    ("Beef bulgogi", "East Asian", "beef", ["soy_sauce", "sesame_oil", "pear", "garlic", "scallion", "gochujang", "rice"], ["tofu", "mushroom"]),
    ("Teriyaki chicken", "East Asian", "chicken", ["soy_sauce", "mirin", "sake", "ginger", "sesame_seed", "rice"], ["tofu"]),
    ("Pork dumplings", "East Asian", "pork", ["cabbage", "ginger", "scallion", "soy_sauce", "sesame_oil", "wonton_wrapper"], ["tofu", "mushroom"]),
    ("Thai green curry", "Southeast Asian", "chicken", ["green_curry_paste", "coconut_milk", "thai_basil", "lime_leaf", "fish_sauce", "eggplant"], ["tofu"]),
    ("Pad thai with shrimp", "Southeast Asian", "shrimp", ["rice_noodle", "tamarind", "peanut", "bean_sprout", "lime", "fish_sauce", "egg"], ["tofu"]),
    ("Pho bo", "Southeast Asian", "beef", ["rice_noodle", "star_anise", "cinnamon", "ginger", "fish_sauce", "thai_basil", "lime"], ["tofu", "mushroom"]),
    ("Beef rendang", "Southeast Asian", "beef", ["coconut_milk", "lemongrass", "galangal", "chili_pepper", "turmeric", "lime_leaf"], ["jackfruit", "tofu", "tempeh"]),
    ("Chicken satay", "Southeast Asian", "chicken", ["peanut", "soy_sauce", "lemongrass", "turmeric", "coconut_milk", "lime"], ["tofu", "tempeh"]),
    ("Spaghetti bolognese", "Mediterranean", "beef", ["pasta", "tomato", "onion", "carrot", "celery", "parmesan_cheese", "red_wine"], ["lentil", "mushroom"]),
    ("Lasagna", "Mediterranean", "beef", ["pasta", "tomato", "ricotta_cheese", "mozzarella_cheese", "basil", "oregano"], ["lentil", "mushroom", "eggplant"]),
    ("Moussaka", "Mediterranean", "lamb", ["eggplant", "tomato", "cinnamon", "nutmeg", "onion", "oregano"], ["lentil"]),
    ("Chicken shawarma", "Mediterranean", "chicken", ["cumin", "paprika", "garlic", "lemon", "pita_bread", "tahini"], ["chickpea"]),
    ("Lamb kofta", "Mediterranean", "lamb", ["cumin", "coriander", "parsley", "onion", "garlic", "yogurt"], ["chickpea", "lentil"]),
    ("Meatballs in tomato sauce", "Mediterranean", "beef", ["breadcrumb", "parmesan_cheese", "tomato", "basil", "garlic", "egg"], ["lentil", "mushroom"]),
    ("Beef burger", "Western", "beef", ["bun", "lettuce", "tomato", "onion", "ketchup", "mustard", "cheddar_cheese"], ["black_bean", "mushroom"]),
    ("Shepherd's pie", "Western", "lamb", ["potato", "carrot", "green_pea", "onion", "thyme", "worcestershire_sauce"], ["lentil", "mushroom"]),
    ("Pulled pork", "Western", "pork", ["barbecue_sauce", "brown_sugar", "paprika", "apple_cider_vinegar", "bun", "coleslaw"], ["jackfruit"]),
    ("Beef stew", "Western", "beef", ["potato", "carrot", "celery", "thyme", "bay_leaf", "red_wine"], ["mushroom", "lentil"]),
    ("Beef goulash", "Eastern European", "beef", ["paprika", "onion", "caraway_seed", "tomato", "potato", "bell_pepper"], ["mushroom"]),
    ("Beef stroganoff", "Eastern European", "beef", ["sour_cream", "mushroom", "onion", "egg_noodle", "dill", "mustard"], ["mushroom"]),
]


def evaluate(model="core"):
    emb = load(model)
    cands = [c for c in C.CANDIDATES["meat"] if c in emb]
    methods = {"ours_cuisine_lock": [], "ours_no_lock": [], "nearest_to_meat": [],
               "always_tofu": [], "random": []}
    rows, skipped = [], []
    for dish, cuisine, meat, ctx, gold in DISHES:
        ctx_in = [x for x in ctx if x in emb]
        missing = [x for x in ctx if x not in emb]
        gold = [g for g in gold if g in cands]
        if len(ctx_in) < 4 or not gold:
            skipped.append(dish)
            continue
        cvec = emb.centroid(ctx_in)
        pole = emb.cuisines[emb.detect_cuisine(ctx_in)[0][0]]
        lock = [c["name"] for c in rank_swaps(meat, cvec, pole, "vegan", emb)]
        nolock = [c["name"] for c in rank_swaps(meat, cvec, None, "vegan", emb)]
        allowed = set(lock)  # same diet + footprint filter for every method
        near = sorted(allowed, key=lambda c: -emb.sim(c, emb.vec(meat)))
        tofu = ["tofu"] + [c for c in near if c != "tofu"]
        for name, ranking in [("ours_cuisine_lock", lock), ("ours_no_lock", nolock),
                              ("nearest_to_meat", near), ("always_tofu", tofu)]:
            methods[name].append((ranking[0] in gold, any(g in ranking[:3] for g in gold)))
        # Random: exact expected hit rates over a uniform shuffle of the allowed list
        n, g = len(allowed), len(set(gold) & allowed)
        p1 = g / n
        p3 = 1 - np.prod([(n - g - i) / (n - i) for i in range(3)]) if n >= 3 else 1.0
        methods["random"].append((p1, p3))
        rows.append({"dish": dish, "cuisine": cuisine, "meat": meat, "gold": gold,
                     "ours_top3": lock[:3], "hit1": lock[0] in gold, "missing_context": missing})
    summary = {m: {"hit_at_1": round(float(np.mean([v[0] for v in vals])), 3),
                   "hit_at_3": round(float(np.mean([v[1] for v in vals])), 3)}
               for m, vals in methods.items()}
    return {"model": model, "n_dishes": len(rows), "skipped": skipped,
            "summary": summary, "rows": rows}


if __name__ == "__main__":
    results = {m: evaluate(m) for m in ("core", "cooc", "chem")}
    out = ROOT / "data" / "benchmark_results.json"
    out.write_text(json.dumps(results, indent=1))
    for m, r in results.items():
        print(f"\n== epicure-{m}  (n={r['n_dishes']}, skipped={r['skipped']})")
        for k, v in r["summary"].items():
            print(f"  {k:20s} hit@1 {v['hit_at_1']:.0%}   hit@3 {v['hit_at_3']:.0%}")
    print("\nPer dish (core, cuisine lock):")
    for row in results["core"]["rows"]:
        mark = "✓" if row["hit1"] else ("~" if any(g in row["ours_top3"] for g in row["gold"]) else "✗")
        print(f"  {mark} {row['dish']:26s} gold={row['gold']}  ours={row['ours_top3']}"
              + (f"  (not in vocab: {row['missing_context']})" if row["missing_context"] else ""))
