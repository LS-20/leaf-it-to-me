// Recipe Remix front end: plain JS, no build step.
const $ = (sel) => document.querySelector(sel);

const state = {
  recipe: null,          // {title, ingredients: [{name, grams}]}
  pantry: [],            // free-text names
  mode: "vegan",
  model: "core",
  cuisineLock: true,
  overrides: {},         // {original ingredient name: chosen swap}
  hasResult: false,
};

const EMOJI = { butter_chicken: "🍛", beef_tacos: "🌮", bolognese: "🍝", mapo_tofu: "🥢" };
const METRICS = [
  { key: "ghg", name: "Greenhouse gas", unit: "kg CO₂e", digits: 1 },
  { key: "land", name: "Land use", unit: "m²", digits: 1 },
  { key: "water", name: "Freshwater", unit: "L", digits: 0 },
];

// ---------- helpers ----------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const pretty = (s) => String(s || "").replace(/_/g, " ");
const fmt = (n, d) => Number(n).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d });

function toast(msg, ms = 3500) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add("hidden"), ms);
}
function loading(on, text = "Working…") {
  $("#loadingText").textContent = text;
  $("#loading").classList.toggle("hidden", !on);
}
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON error */ }
  if (!res.ok) throw new Error((data && data.detail && (data.detail.msg || data.detail)) || `Request failed (${res.status})`);
  return data;
}
const postJSON = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------- step 1: recipe ----------
document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".tabpane").forEach((p) =>
      p.classList.toggle("hidden", p.id !== `tab-${tab.dataset.tab}`));
  }));

async function loadSamples() {
  const list = await api("/api/samples");
  $("#samples").innerHTML = list.map((s) => `
    <button class="sample" data-key="${esc(s.key)}">
      <span class="emoji">${EMOJI[s.key] || "🍽️"}</span>${esc(s.title)}
    </button>`).join("");
  document.querySelectorAll(".sample").forEach((b) =>
    b.addEventListener("click", async () => {
      document.querySelectorAll(".sample").forEach((x) => x.classList.toggle("active", x === b));
      setRecipe(await api(`/api/samples/${b.dataset.key}`), true);
    }));
}

$("#pasteBtn").addEventListener("click", async () => {
  const text = $("#pasteText").value.trim();
  if (text.length < 3) return toast("Paste a recipe first.");
  loading(true, "Gemini is reading your recipe…");
  try {
    setRecipe(await postJSON("/api/parse/text", { text }), true);
  } catch (e) { toast(e.message); } finally { loading(false); }
});

async function uploadPhoto(file, kind) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("kind", kind);
  return api("/api/parse/photo", { method: "POST", body: fd });
}

$("#recipePhoto").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  loading(true, "Gemini is reading your recipe photo…");
  try {
    setRecipe(await uploadPhoto(file, "recipe"), true);
  } catch (err) { toast(err.message); } finally { loading(false); e.target.value = ""; }
});

function setRecipe(recipe, run) {
  state.recipe = {
    title: recipe.title || "Your recipe",
    ingredients: recipe.ingredients.map((i) => ({ name: i.name, grams: Math.round(i.grams || 0) })),
  };
  state.overrides = {};
  renderIngredients();
  $("#remixBtn").disabled = false;
  if (run) doRemix();
}

function renderIngredients() {
  const r = state.recipe;
  $("#ingredientsBox").classList.remove("hidden");
  $("#dishTitle").value = r.title;
  $("#ingCount").textContent = `${r.ingredients.length} ingredients`;
  $("#ingTable").innerHTML = r.ingredients.map((i, k) => `
    <div class="ing-row" data-k="${k}">
      <input class="n" value="${esc(i.name)}" aria-label="Ingredient">
      <input class="g" type="number" min="0" step="5" value="${esc(i.grams)}" aria-label="Grams">
      <span class="unit">g</span>
      <button class="del" title="Remove" aria-label="Remove ${esc(i.name)}">×</button>
    </div>`).join("");
  document.querySelectorAll(".ing-row").forEach((row) => {
    const k = +row.dataset.k;
    row.querySelector(".n").addEventListener("change", (e) => { r.ingredients[k].name = e.target.value.trim(); markDirty(); });
    row.querySelector(".g").addEventListener("change", (e) => { r.ingredients[k].grams = Math.max(0, +e.target.value || 0); markDirty(); });
    row.querySelector(".del").addEventListener("click", () => { r.ingredients.splice(k, 1); renderIngredients(); markDirty(); });
  });
}
$("#dishTitle").addEventListener("change", (e) => { if (state.recipe) state.recipe.title = e.target.value; });
$("#addIng").addEventListener("click", () => {
  state.recipe.ingredients.push({ name: "", grams: 100 });
  renderIngredients();
  const rows = document.querySelectorAll(".ing-row .n");
  rows[rows.length - 1].focus();
});
function markDirty() {
  if (state.hasResult) $("#remixBtn").textContent = "Update remix →";
}

// ---------- step 2: pantry ----------
function renderPantry() {
  $("#pantryChips").innerHTML = state.pantry.map((p, k) => `
    <span class="chip">${esc(p)}<button data-k="${k}" aria-label="Remove ${esc(p)}">×</button></span>`).join("");
  document.querySelectorAll("#pantryChips button").forEach((b) =>
    b.addEventListener("click", () => { state.pantry.splice(+b.dataset.k, 1); renderPantry(); rerun(); }));
}
function addPantry(items) {
  const seen = new Set(state.pantry.map((p) => p.toLowerCase()));
  items.forEach((i) => { const t = i.trim(); if (t && !seen.has(t.toLowerCase())) { state.pantry.push(t); seen.add(t.toLowerCase()); } });
  renderPantry();
  rerun();
}
$("#pantryForm").addEventListener("submit", (e) => {
  e.preventDefault();
  addPantry($("#pantryInput").value.split(","));
  $("#pantryInput").value = "";
});
$("#pantryPhoto").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  loading(true, "Gemini is looking at your pantry…");
  try {
    const { items } = await uploadPhoto(file, "pantry");
    if (!items.length) toast("Couldn't spot any food in that photo.");
    else toast(`Found ${items.length} items in your pantry.`);
    addPantry(items);
  } catch (err) { toast(err.message); } finally { loading(false); e.target.value = ""; }
});

// ---------- step 3: settings ----------
function segmented(sel, attr, key) {
  document.querySelectorAll(`${sel} button`).forEach((b) =>
    b.addEventListener("click", () => {
      document.querySelectorAll(`${sel} button`).forEach((x) => {
        x.classList.toggle("active", x === b);
        x.setAttribute("aria-checked", x === b);
      });
      state[key] = b.dataset[attr];
      rerun();
    }));
}
segmented("#modeSeg", "mode", "mode");
segmented("#modelSeg", "model", "model");
$("#cuisineLock").addEventListener("change", (e) => { state.cuisineLock = e.target.checked; rerun(); });
$("#remixBtn").addEventListener("click", doRemix);
function rerun() { if (state.hasResult) doRemix(); }

// ---------- remix ----------
async function doRemix() {
  if (!state.recipe) return;
  const ingredients = state.recipe.ingredients.filter((i) => i.name);
  if (!ingredients.length) return toast("Add at least one ingredient.");
  try {
    const r = await postJSON("/api/remix", {
      title: state.recipe.title, ingredients, mode: state.mode, model: state.model,
      cuisine_lock: state.cuisineLock, pantry: state.pantry, overrides: state.overrides,
    });
    state.hasResult = true;
    state.lastResult = r;
    $("#remixBtn").textContent = "Remix it →";
    renderResult(r);
  } catch (e) { toast(e.message); }
}

function renderResult(r) {
  $("#emptyState").classList.add("hidden");
  const el = $("#result");
  el.classList.remove("hidden");
  const b = r.footprint_before, a = r.footprint_after;
  const pct = b.ghg ? ((a.ghg - b.ghg) / b.ghg) * 100 : 0;
  const cuisine = r.cuisine?.[0]?.[0];
  const pantryUsed = r.swaps.filter((s) => s.in_pantry).length;

  const bars = METRICS.map((m) => {
    const max = Math.max(b[m.key], a[m.key]) || 1;
    const d = b[m.key] ? ((a[m.key] - b[m.key]) / b[m.key]) * 100 : 0;
    const up = d > 0.5;
    return `
      <div>
        <div class="metric-head"><span class="name">${m.name}</span>
          <span class="delta ${up ? "up" : ""}">${d > 0 ? "+" : ""}${fmt(d, 0)}%</span></div>
        <div class="bar-pair">
          <div class="bar"><span>Before</span><div class="track"><div class="fill before" data-w="${(b[m.key] / max) * 100}"></div></div>
            <span class="val">${fmt(b[m.key], m.digits)} ${m.unit}</span></div>
          <div class="bar"><span>After</span><div class="track"><div class="fill after ${up ? "up" : ""}" data-w="${(a[m.key] / max) * 100}"></div></div>
            <span class="val">${fmt(a[m.key], m.digits)} ${m.unit}</span></div>
        </div>
      </div>`;
  }).join("");

  const swaps = r.swaps.length ? r.swaps.map((s, i) => `
    <div class="swap" style="animation-delay:${i * 70}ms">
      <div class="swap-main">
        <span class="from">${esc(s.from)}</span><span class="arrow">→</span>
        <span class="to">${esc(pretty(s.to))}</span>
        <span class="grams">${fmt(s.grams, 0)} g</span>
      </div>
      <div class="swap-meta">
        ${s.in_pantry ? '<span class="badge pantry">✓ in your pantry</span>' : ""}
        ${s.user_choice ? '<span class="badge">your pick</span>' : ""}
        <span class="meter" title="How well it fits the rest of the dish (cosine similarity)">dish fit <span class="m"><i style="width:${Math.max(0, s.fit) * 100}%"></i></span></span>
        ${r.cuisine_lock && cuisine ? `<span class="meter" title="How close it sits to the ${esc(pretty(cuisine))} cuisine direction">${esc(pretty(cuisine))} fit <span class="m"><i style="width:${Math.max(0, s.cuisine_fit) * 100}%"></i></span></span>` : ""}
        ${s.proxy ? '<span title="Footprint uses the closest food category">≈ footprint estimate</span>' : ""}
        ${s.ghg_per_kg == null ? '<span>footprint unknown</span>' : ""}
      </div>
      ${s.alternatives.length ? `<div class="alts">Also plausible:
        ${s.alternatives.map((alt) => `<button class="alt ${alt.in_pantry ? "pantry" : ""}" data-from="${esc(s.from)}" data-to="${esc(alt.name)}">${alt.in_pantry ? "✓ " : ""}${esc(pretty(alt.name))}</button>`).join("")}
      </div>` : ""}
    </div>`).join("")
    : `<div class="note ok">This dish already fits a ${esc(r.mode)} diet. Nothing to swap. 🎉</div>`;

  const nutri = r.nutrient_flags.length ? `
    <div class="note nutri"><h3>🥦 Nutrients to watch <span class="muted small">(not medical advice)</span></h3><ul>
      ${r.nutrient_flags.map((n) => `<li><strong>${esc(n.nutrient)}</strong> (was in ${esc(n.lost_from.join(", "))}): ${esc(n.tip)}</li>`).join("")}
    </ul></div>` : "";
  const warns = r.warnings.length ? `
    <div class="note warn"><h3>⚠️ Check these</h3><ul>
      ${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}
    </ul></div>` : "";

  el.innerHTML = `
    <div class="card">
      <div class="result-head"><h2>${esc(r.title)}</h2></div>
      <div class="badges">
        ${cuisine ? `<span class="badge cuisine">${esc(pretty(cuisine))} cuisine</span>` : ""}
        <span class="badge">${esc(r.mode)}</span>
        <span class="badge">Epicure ${esc(r.model)}</span>
        ${pantryUsed ? `<span class="badge pantry">${pantryUsed} swap${pantryUsed > 1 ? "s" : ""} from your pantry</span>` : ""}
      </div>
      <div class="hero">
        <div class="big-pct ${pct > 0 ? "up" : ""}">${pct > 0 ? "+" : "−"}${fmt(Math.abs(pct), 0)}%</div>
        <div class="hero-label">greenhouse gas for the whole recipe<br>
          <strong>${fmt(b.ghg, 1)} → ${fmt(a.ghg, 1)} kg CO₂e</strong>
          ${b.ghg - a.ghg > 0.5 ? `<br>≈ ${fmt((b.ghg - a.ghg) / 0.4, 0)} miles not driven*` : ""}</div>
      </div>
      <div class="bars">${bars}</div>
      ${(a.land > b.land * 1.005 || a.water > b.water * 1.005) ? `<div class="coverage"><strong>Trade-off:</strong> some swaps use more ${a.land > b.land * 1.005 && a.water > b.water * 1.005 ? "land or water" : a.land > b.land * 1.005 ? "land" : "water"} than what they replace (pulses need more land per kg than chicken; nuts like cashews are water-hungry). Tap an alternative swap to compare.</div>` : ""}
      <div class="coverage">Footprint data covers ${fmt(b.coverage * 100, 0)}% of the recipe by weight (butter, cream, oils and spices aren't in the dataset).
        ${b.ghg - a.ghg > 0.5 ? "*Using the US EPA estimate of about 0.4 kg CO₂ per mile for a typical passenger car." : ""}</div>
    </div>
    <div class="card">
      <h3 class="section-title">Swaps <span class="muted small">highest impact first</span></h3>
      <div class="swaps">${swaps}</div>
    </div>
    ${nutri || warns ? `<div class="card notes">${nutri}${warns}</div>` : ""}`;

  requestAnimationFrame(() => requestAnimationFrame(() =>
    el.querySelectorAll(".fill").forEach((f) => { f.style.width = `${f.dataset.w}%`; })));

  el.querySelectorAll(".alt").forEach((btn) =>
    btn.addEventListener("click", () => { state.overrides[btn.dataset.from] = btn.dataset.to; doRemix(); }));
  renderPantry();
  if (window.innerWidth < 920 && !renderResult._scrolled) {
    renderResult._scrolled = true;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

loadSamples().catch((e) => toast(e.message));
