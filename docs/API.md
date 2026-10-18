# Leaf It To Me API

All app logic lives on the server, so any client (the web app, or a future SwiftUI app) is just screens on top of these endpoints. JSON in, JSON out.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/samples` | – | `[{key, title}]` |
| GET | `/api/samples/{key}` | – | `{title, ingredients: [{name, grams}]}` |
| POST | `/api/parse/text` | `{text}` | `{title, ingredients: [{name, grams}]}` (Gemini) |
| POST | `/api/parse/photo` | multipart: `file`, `kind` = `recipe` or `pantry` | recipe: `{title, ingredients}`; pantry: `{items: [string]}` (Gemini) |
| POST | `/api/remix` | see below | see below |
| GET | `/api/flavor-map` | – | `{regions: [{name, x, y}], points: [{n, x, y}]}` (x, y in 0..1) |
| GET | `/api/benchmark` | – | accuracy results per Epicure model |

## POST /api/remix

Request:

```json
{
  "title": "Butter chicken",
  "ingredients": [{"name": "chicken thighs", "grams": 700}, {"name": "heavy cream", "grams": 120}],
  "mode": "vegan",                 // flexitarian | vegetarian | vegan
  "model": "core",                 // core | cooc | chem
  "cuisine_lock": true,
  "pantry": ["chickpeas", "coconut milk"],
  "overrides": {"chicken thighs": "tofu"}   // optional: user picked an alternative
}
```

Response (main fields):

```json
{
  "title": "Butter chicken", "mode": "vegan",
  "cuisine": [["South_Asian", 0.92], ["Western_Atlantic", 0.87], ["Mediterranean", 0.86]],
  "swaps": [{
    "from": "chicken thighs", "from_epicure": "chicken", "grams": 700, "role": "meat",
    "to": "chickpea", "fit": 0.75, "cuisine_fit": 0.82, "in_pantry": true, "user_choice": false,
    "alternatives": [{"name": "chana_dal", "fit": 0.74, "cuisine_fit": 0.82, "in_pantry": false}],
    "why": [{"name": "kashmiri_chili", "sim": 0.71}, {"name": "fenugreek_leaf", "sim": 0.70}]
  }],
  "before": [{"name": "...", "grams": 0, "epicure": "...", "diet": "vegan|vegetarian|animal|check"}],
  "after":  [ /* same shape, with swaps applied */ ],
  "footprint_before": {"ghg": 9.55, "land": 10.9, "water": 1363, "coverage": 0.90},
  "footprint_after":  {"ghg": 3.62, "land": 15.2, "water": 2122, "coverage": 0.96},
  "nutrient_flags": [{"nutrient": "vitamin B12", "lost_from": ["chicken thighs"], "tip": "..."}],
  "warnings": ["Check label: ..."],
  "pantry_matched": ["chickpea", "coconut_milk"],
  "dish_epicure": ["garam_masala", "tomato", "..."]
}
```

Names with underscores are Epicure vocabulary names; show them with spaces. `ghg` is kg CO2e for the whole recipe.

## SwiftUI notes

- `Codable` structs for the request and response above; `URLSession` for calls.
- Photo input: `PhotosPicker` or a camera sheet, then send JPEG data as multipart to `/api/parse/photo`.
- The flavor map can be drawn with SwiftUI `Canvas` from `/api/flavor-map` points.
