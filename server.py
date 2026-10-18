"""Web server: wraps the remix engine in a small JSON API and serves the page.

Run locally:  .venv/bin/uvicorn server:app --reload
Then open:    http://localhost:8000
"""
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from remix import adapters
from remix.images import downscale
from remix.samples import SAMPLES
from remix.swap import remix

ROOT = Path(__file__).resolve().parent
MAX_UPLOAD = 15 * 1024 * 1024
app = FastAPI(title="Recipe Remix")


class Ingredient(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    grams: float = Field(ge=0, le=20000)


class RemixRequest(BaseModel):
    title: str = "Your recipe"
    ingredients: list[Ingredient] = Field(min_length=1, max_length=60)
    mode: str = Field("vegan", pattern="^(flexitarian|vegetarian|vegan)$")
    model: str = Field("core", pattern="^(core|cooc|chem)$")
    cuisine_lock: bool = True
    pantry: list[str] = Field(default_factory=list, max_length=100)
    overrides: dict[str, str] = Field(default_factory=dict)


class TextRequest(BaseModel):
    text: str = Field(min_length=3, max_length=8000)


@app.get("/api/samples")
def samples():
    return [{"key": k, "title": v["title"]} for k, v in SAMPLES.items()]


@app.get("/api/samples/{key}")
def sample(key: str):
    if key not in SAMPLES:
        raise HTTPException(404, "Unknown sample")
    return adapters.sample(key)


@app.get("/api/flavor-map")
def flavor_map():
    """2D t-SNE layout of all 1,790 Epicure ingredients (precomputed)."""
    return FileResponse(ROOT / "data" / "flavor_map.json", media_type="application/json")


@app.post("/api/parse/text")
def parse_text(req: TextRequest):
    try:
        return adapters.text(req.text)
    except Exception as e:
        raise HTTPException(502, f"Couldn't read that recipe: {e}")


async def _read_image(file: UploadFile):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Photo is too large (15 MB max)")
    return downscale(data, file.content_type or "image/jpeg")


@app.post("/api/parse/photo")
async def parse_photo(file: UploadFile = File(...), kind: str = Form("recipe")):
    img = await _read_image(file)
    try:
        if kind == "pantry":
            return {"items": adapters.pantry_photo(img)}
        return adapters.photo(img)
    except Exception as e:
        raise HTTPException(502, f"Couldn't read that photo: {e}")


@app.post("/api/remix")
def do_remix(req: RemixRequest):
    recipe = {"title": req.title,
              "ingredients": [i.model_dump() for i in req.ingredients]}
    return remix(recipe, mode=req.mode, model=req.model, cuisine_lock=req.cuisine_lock,
                 pantry=req.pantry, overrides=req.overrides)


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
