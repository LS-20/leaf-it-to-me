"""The remix pipeline: map -> footprint -> pick what to replace -> rank swaps.

Rule: embeddings PROPOSE (rank candidates by fit with the dish and its cuisine);
the rule table in catalog.py DECIDES what is allowed.
"""
from . import catalog as C
from .embeddings import load
from .footprint import per_kg, recipe_footprint
from .mapping import map_name

MIN_CUT = 0.30       # a swap must cut CO2e per kg by at least 30% (when both are known)
CUISINE_WEIGHT = 0.5  # share of the score from the detected cuisine pole


def needs_swap(name, mode):
    status = C.diet_status(name)
    if mode == "flexitarian":
        return name in C.RUMINANT
    if mode == "vegan" and status == C.CHECK and C.role_of(name):
        return True  # e.g. cheddar: never vegan, whatever the rennet
    return status in (C.ANIMAL, C.VEGETARIAN) and status not in C.ALLOWED[mode]


def rank_swaps(original, context_vec, cuisine_vec, mode, emb, pantry=()):
    role = C.role_of(original)
    orig_f = per_kg(original)
    out = []
    for cand in C.CANDIDATES.get(role, []):
        if cand not in emb or C.diet_status(cand) not in C.ALLOWED[mode]:
            continue
        f = per_kg(cand)
        if orig_f and f and f["ghg"] > orig_f["ghg"] * (1 - MIN_CUT):
            continue  # not a big enough footprint win (e.g. paneer vs chicken)
        fit = emb.sim(cand, context_vec) if context_vec is not None else 0.0
        cui = emb.sim(cand, cuisine_vec) if cuisine_vec is not None else 0.0
        score = (1 - CUISINE_WEIGHT) * fit + CUISINE_WEIGHT * cui \
            if cuisine_vec is not None else fit
        if cand in pantry:
            score += 0.10  # prefer what the user already owns (less waste)
        out.append({"name": cand, "score": round(score, 3), "fit": round(fit, 3),
                    "cuisine_fit": round(cui, 3), "in_pantry": cand in pantry,
                    "ghg_per_kg": f["ghg"] if f else None,
                    "proxy": f["proxy"] if f else None})
    return sorted(out, key=lambda c: -c["score"])


def remix(recipe, mode="vegan", model="core", cuisine_lock=True, pantry=()):
    emb = load(model)
    vocab = emb.names
    items = []
    for ing in recipe["ingredients"]:
        m = map_name(ing["name"], vocab)
        e = m["epicure"]
        items.append({
            "name": ing["name"], "grams": float(ing.get("grams") or 0),
            "epicure": e, "map_method": m["method"],
            "diet": C.diet_status(e) if e else C.CHECK,
            "footprint": per_kg(e) if e else None,
        })

    mapped = [i["epicure"] for i in items if i["epicure"] in emb]
    cuisines = emb.detect_cuisine(mapped)
    cuisine_vec = emb.cuisines[cuisines[0][0]] if (cuisine_lock and cuisines) else None

    to_swap = [i for i in items if i["epicure"] and needs_swap(i["epicure"], mode)]
    # Context = the dish minus the things we are replacing.
    keep = [i["epicure"] for i in items if i["epicure"] in emb and i not in to_swap]
    context_vec = emb.centroid(keep)

    after = [dict(i) for i in items]
    swaps, warnings, nutrients = [], [], {}
    # Highest-impact first (grams x CO2e/kg).
    to_swap.sort(key=lambda i: -(i["grams"] * (i["footprint"] or {}).get("ghg", 0)))
    for it in to_swap:
        ranked = rank_swaps(it["epicure"], context_vec, cuisine_vec, mode, emb, pantry)
        if not ranked:
            warnings.append(f"No allowed swap found for {it['name']}: remove it or check a specialty product.")
            continue
        best = ranked[0]
        role = C.role_of(it["epicure"])
        for n in C.NUTRIENT_FLAGS.get(role, []):
            nutrients.setdefault(n, []).append(it["name"])
        for a in after:
            if a["epicure"] == it["epicure"] and a["name"] == it["name"]:
                a.update(epicure=best["name"], name=best["name"].replace("_", " "),
                         diet=C.diet_status(best["name"]), footprint=per_kg(best["name"]),
                         swapped_from=it["name"])
        swaps.append({"from": it["name"], "from_epicure": it["epicure"],
                      "grams": it["grams"], "role": role,
                      "to": best["name"], "alternatives": ranked[1:4], **best})

    for a in after:
        if a["diet"] == C.CHECK and a["epicure"] and C.check_concerns(a["epicure"], mode):
            warnings.append(f"Check label: {a['name']} (processed or unclassified; may hide animal ingredients).")
        if a["epicure"] is None:
            warnings.append(f"Not recognized: {a['name']} (not in footprint or diet check; check it yourself).")

    before_fp, after_fp = recipe_footprint(items), recipe_footprint(after)
    return {
        "title": recipe.get("title", "Your recipe"), "mode": mode, "model": model,
        "cuisine": cuisines[:3], "cuisine_lock": cuisine_lock,
        "before": items, "after": after, "swaps": swaps,
        "footprint_before": before_fp, "footprint_after": after_fp,
        "nutrient_flags": [{"nutrient": n, "lost_from": v, "tip": C.NUTRIENT_TIPS.get(n, "")}
                           for n, v in nutrients.items()],
        "warnings": list(dict.fromkeys(warnings)),
    }
