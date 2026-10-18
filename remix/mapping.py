"""Map free-text ingredient names to Epicure's 1,790-name vocabulary.

Order: alias table -> exact -> longest sub-phrase -> fuzzy. Unmapped items are
reported, never guessed.
"""
import re

from rapidfuzz import fuzz, process

ALIASES = {
    "ground beef": "beef", "minced beef": "beef", "steak": "beef",
    "chicken thigh": "chicken", "chicken breast": "chicken",
    "heavy cream": "cream", "double cream": "cream", "whipping cream": "cream",
    "single cream": "cream", "half and half": "cream",
    "cilantro": "coriander", "coriander leaves": "coriander",
    "spaghetti": "pasta", "penne": "pasta", "linguine": "pasta",
    "garbanzo": "chickpea", "garbanzo bean": "chickpea",
    "kasuri methi": "fenugreek_leaf", "dried fenugreek leaves": "fenugreek_leaf",
    "green onion": "scallion", "spring onion": "scallion",
    "chicken stock": "chicken_broth", "beef stock": "beef_broth",
    "vegetable broth": "vegetable_stock",
    "ground pork": "pork", "minced pork": "pork",
    "parmesan": "parmesan_cheese", "parmigiano reggiano": "parmesan_cheese",
    "cheddar": "cheddar_cheese", "mozzarella": "mozzarella_cheese",
    "chile powder": "chili_powder", "egg": "egg", "eggs": "egg",
    "corn tortilla": "tortilla", "flour tortilla": "tortilla",
    "vegetable oil": "vegetable_oil", "canola oil": "vegetable_oil",
    "doubanjiang": "doubanjiang", "chili bean paste": "doubanjiang",
    "sichuan pepper": "sichuan_peppercorn",
}
DESCRIPTORS = {"fresh", "dried", "chopped", "minced", "diced", "sliced", "large",
               "small", "medium", "boneless", "skinless", "ground", "whole",
               "finely", "roughly", "grated", "crushed", "lean", "extra", "virgin",
               "unsalted", "salted", "organic", "raw", "cooked", "canned", "of",
               "can", "cans", "and", "or", "to", "taste", "optional", "pieces"}


def _singular(w):
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("oes"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def normalize(text: str) -> str:
    t = re.sub(r"\(.*?\)", " ", text.lower())
    t = re.sub(r"[^a-z\s-]", " ", t).replace("-", " ")
    return " ".join(_singular(w) for w in t.split())


def map_name(raw: str, vocab) -> dict:
    """Return {"epicure": name|None, "method": str}."""
    t = normalize(raw)
    for key in (t, " ".join(w for w in t.split() if w not in DESCRIPTORS)):
        if key in ALIASES:
            return {"epicure": ALIASES[key], "method": "alias"}
        cand = key.replace(" ", "_")
        if cand in vocab:
            return {"epicure": cand, "method": "exact"}
    words = [w for w in t.split() if w not in DESCRIPTORS]
    # Longest contiguous sub-phrase that is in the vocab ("boneless chicken thighs" -> chicken)
    for n in range(len(words), 0, -1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i + n])
            if phrase in ALIASES:
                return {"epicure": ALIASES[phrase], "method": "alias"}
            if phrase.replace(" ", "_") in vocab:
                return {"epicure": phrase.replace(" ", "_"), "method": "subphrase"}
    if words:
        best = process.extractOne("_".join(words), vocab, scorer=fuzz.ratio)
        if best and best[1] >= 88:
            return {"epicure": best[0], "method": f"fuzzy({best[1]:.0f})"}
    return {"epicure": None, "method": "unmapped"}
