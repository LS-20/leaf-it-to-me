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
    if C.allowed(name, mode):
        return False
    if mode == "vegan" and status == C.CHECK and C.role_of(name):
        return True  # e.g. cheddar: never vegan, whatever the rennet
    return status in (C.ANIMAL, C.VEGETARIAN) and status not in C.ALLOWED[mode]


def rank_swaps(original, context_vec, cuisine_vec, mode, emb, pantry=()):
    role = C.role_of(original)
    orig_f = per_kg(original)
    out = []
    cands = list(C.CANDIDATES.get(role, []))
    if mode == "pescetarian" and role in ("meat", "seafood"):
        cands += C.SEAFOOD_SWAPS
    for cand in cands:
        if cand == original or cand not in emb or not C.allowed(cand, mode):
            continue
        if cand in C.SEAFOOD and per_kg(cand) is None:
            continue  # no footprint data: don't guess
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


def build_graph(emb, after, swaps, k=3, min_w=0.35):
    """Flavor graph of the remixed dish.

    Nodes: ingredients after the remix (kept + new) and the removed originals.
    Edges: each node links to its k most similar dish ingredients (cosine, Epicure),
    plus a 'swap' edge from each removed ingredient to its replacement.
    """
    names = list(dict.fromkeys(a["epicure"] for a in after if a.get("epicure") in emb))
    new_of = {s["to"]: i for i, s in enumerate(swaps)}
    nodes = [{"id": n, "label": n.replace("_", " "), "group": C.group_of(n),
              "kind": "new" if n in new_of else "kept", "swap": new_of.get(n)} for n in names]
    for i, s in enumerate(swaps):
        if s["from_epicure"] in emb and s["from_epicure"] not in names:
            nodes.append({"id": s["from_epicure"], "label": s["from_epicure"].replace("_", " "),
                          "group": C.group_of(s["from_epicure"]), "kind": "removed", "swap": i})
    if not names:
        return {"nodes": nodes, "edges": []}
    V = emb.E[[emb.index[n] for n in names]]
    S = V @ V.T
    edges = {}
    for a in range(len(names)):
        order = [b for b in S[a].argsort()[::-1] if b != a][:k]
        for b in order:
            w = float(S[a, b])
            if w >= min_w:
                key = tuple(sorted((names[a], names[b])))
                edges[key] = round(w, 3)
    out = [{"a": a, "b": b, "w": w, "kind": "pair"} for (a, b), w in edges.items()]
    for s in swaps:
        if s["from_epicure"] in emb:
            out.append({"a": s["from_epicure"], "b": s["to"], "w": 1.0, "kind": "swap"})
    return {"nodes": nodes, "edges": out}


def alternatives(ranked, best, mode, n=4):
    """Next-best swaps. In pescetarian mode, always show the best seafood option
    (if one passed the footprint filter), since it would rarely make the top few."""
    alts = [c for c in ranked if c["name"] != best["name"]]
    if mode == "pescetarian":
        fish = next((c for c in alts if c["name"] in C.SEAFOOD), None)
        if fish:  # lead with it so it's visible
            alts = [fish] + [c for c in alts if c is not fish]
    return alts[:n]


def remix(recipe, mode="vegan", model="core", cuisine_lock=True, pantry=(),
          overrides=None):
    """pantry: free-text names the user owns. overrides: {original_name: chosen_swap}."""
    emb = load(model)
    vocab = emb.names
    overrides = overrides or {}
    pantry_set = set()
    for p in pantry:
        e = map_name(p, vocab)["epicure"]
        if e:
            pantry_set.add(e)
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
        ranked = rank_swaps(it["epicure"], context_vec, cuisine_vec, mode, emb, pantry_set)
        if not ranked:
            warnings.append(f"No allowed swap found for {it['name']}: remove it or check a specialty product.")
            continue
        best = ranked[0]
        chosen = overrides.get(it["name"])
        if chosen:
            best = next((c for c in ranked if c["name"] == chosen), best)
        role = C.role_of(it["epicure"])
        for n in C.NUTRIENT_FLAGS.get(role, []):
            if best["name"] in C.SEAFOOD and n in ("vitamin B12", "zinc", "omega-3", "iodine"):
                continue  # fish and shellfish still supply these
            nutrients.setdefault(n, []).append(it["name"])
        for a in after:
            if a["epicure"] == it["epicure"] and a["name"] == it["name"]:
                a.update(epicure=best["name"], name=best["name"].replace("_", " "),
                         diet=C.diet_status(best["name"]), footprint=per_kg(best["name"]),
                         swapped_from=it["name"])
        # Explanation: which of the dish's kept ingredients sit closest to the swap.
        why = sorted(((k, emb.sim(best["name"], emb.vec(k))) for k in set(keep)),
                     key=lambda kv: -kv[1])[:3]
        swaps.append({"why": [{"name": k, "sim": round(v, 3)} for k, v in why],
                      "from": it["name"], "from_epicure": it["epicure"],
                      "grams": it["grams"], "role": role,
                      "to": best["name"], "alternatives": alternatives(ranked, best, mode),
                      "user_choice": best is not ranked[0], **best})

    for a in after:
        if a["diet"] == C.CHECK and a["epicure"] and C.check_concerns(a["epicure"], mode):
            warnings.append(f"Check label: {a['name']} (processed or unclassified; may hide animal ingredients).")
        if a["epicure"] is None:
            warnings.append(f"Not recognized: {a['name']} (not in footprint or diet check; check it yourself).")

    before_fp, after_fp = recipe_footprint(items), recipe_footprint(after)
    return {
        "title": recipe.get("title", "Your recipe"), "mode": mode, "model": model,
        "cuisine": cuisines[:3], "cuisine_lock": cuisine_lock,
        "pantry_matched": sorted(pantry_set),
        "dish_epicure": sorted(set(keep)),
        "graph": build_graph(emb, after, swaps),
        "before": items, "after": after, "swaps": swaps,
        "footprint_before": before_fp, "footprint_after": after_fp,
        "nutrient_flags": [{"nutrient": n, "lost_from": v, "tip": C.NUTRIENT_TIPS.get(n, "")}
                           for n, v in nutrients.items()],
        "warnings": list(dict.fromkeys(warnings)),
    }
