"""Input adapters. Each returns [{"name": str, "grams": float}, ...].

Everything downstream only sees that list (get_ingredients is the seam).
"""
from .llm import call_llm
from .samples import SAMPLES

ING_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "grams": {"type": "number"},
                },
                "required": ["name", "grams"],
            },
        },
    },
    "required": ["ingredients"],
}

RECIPE_PROMPT = """Extract the ingredient list from this recipe.
For each ingredient give a short generic name in English (e.g. "chicken thigh",
"heavy cream", "garam masala") and its weight in grams for the whole recipe.
Convert cups, tablespoons, ounces, pounds and counts to grams with typical
kitchen densities. If no amount is given, estimate a typical amount.
Skip water and salt. Also return a short dish title."""


def sample(key: str):
    s = SAMPLES[key]
    return {"title": s["title"], "ingredients": [dict(i) for i in s["ingredients"]]}


def text(recipe_text: str):
    out = call_llm(RECIPE_PROMPT + "\n\nRECIPE:\n" + recipe_text, schema=ING_SCHEMA)
    return {"title": out.get("title", "Your recipe"), "ingredients": out["ingredients"]}


def photo(payload):
    """payload: (image_bytes, mime_type)."""
    image_bytes, mime = payload
    out = call_llm(RECIPE_PROMPT + "\n\nThe recipe is in the attached photo.",
                   schema=ING_SCHEMA, image=image_bytes, image_mime=mime)
    return {"title": out.get("title", "Your recipe"), "ingredients": out["ingredients"]}


PANTRY_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {"type": "string"}}},
    "required": ["items"],
}
PANTRY_PROMPT = """This is a photo of someone's pantry, fridge or kitchen shelf.
List every distinct food ingredient you can see. Read the labels on cans, jars
and packets. Use short generic English names (e.g. "chickpeas", "coconut milk",
"red lentils", "firm tofu"). Names only, no amounts. Skip non-food items."""


def pantry_photo(payload):
    """payload: (image_bytes, mime_type) -> list of names (available, not amounts)."""
    image_bytes, mime = payload
    out = call_llm(PANTRY_PROMPT, schema=PANTRY_SCHEMA, image=image_bytes, image_mime=mime)
    return list(dict.fromkeys(out["items"]))


def get_ingredients(kind: str, payload):
    return {"sample": sample, "text": text, "photo": photo}[kind](payload)
