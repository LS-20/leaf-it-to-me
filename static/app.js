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
  const saved = b.ghg - a.ghg;
  const pct = b.ghg ? (saved / b.ghg) * 100 : 0;
  const cuisine = r.cuisine?.[0]?.[0];
  const pantryUsed = r.swaps.filter((s) => s.in_pantry).length;

  // The result is the recipe itself: every ingredient line, with swapped lines rewritten.
  const swapByFrom = new Map(r.swaps.map((s, i) => [s.from, { s, i }]));
  const lines = r.before.map((it, k) => {
    const hit = swapByFrom.get(it.name);
    const check = r.after[k]?.diet === "check" && r.mode !== "flexitarian";
    if (!hit) {
      return `<li class="line"><span class="qty">${fmt(it.grams, 0)} g</span>
        <span class="ing">${esc(it.name)}</span>${check ? '<span class="tag warn-tag" title="Processed item: may hide animal ingredients">check label</span>' : ""}</li>`;
    }
    const { s, i } = hit;
    return `<li class="line swap ${i === 0 ? "selected" : ""}" data-i="${i}" style="animation-delay:${i * 80}ms">
      <span class="qty">${fmt(s.grams, 0)} g</span>
      <div class="swap-body">
        <div class="swap-main">
          <span class="from">${esc(s.from)}</span>
          <span class="to">${esc(pretty(s.to))}</span>
          ${s.in_pantry ? '<span class="tag pantry-tag">in your pantry</span>' : ""}
          ${s.user_choice ? '<span class="tag">your pick</span>' : ""}
        </div>
        <div class="swap-meta">
          <span class="meter" title="How well it fits the rest of the dish">dish fit <span class="m"><i style="width:${Math.max(0, s.fit) * 100}%"></i></span></span>
          ${r.cuisine_lock && cuisine ? `<span class="meter" title="How well it fits ${esc(pretty(cuisine))} cooking">${esc(pretty(cuisine))} <span class="m"><i style="width:${Math.max(0, s.cuisine_fit) * 100}%"></i></span></span>` : ""}
          <span class="see-why">why? →</span>
        </div>
        ${s.alternatives.length ? `<div class="alts">or
          ${s.alternatives.map((alt) => `<button class="alt ${alt.in_pantry ? "pantry" : ""}" data-from="${esc(s.from)}" data-to="${esc(alt.name)}">${alt.in_pantry ? "✓ " : ""}${esc(pretty(alt.name))}</button>`).join("")}
        </div>` : ""}
      </div>
    </li>`;
  }).join("");
  const swaps = `${r.swaps.length ? "" : `<div class="note ok">This dish already fits a ${esc(r.mode)} diet. Nothing to swap.</div>`}
    <ol class="recipe">${lines}</ol>`;

  const impact = saved > 0.05 ? `
    <div class="impact">
      <span class="impact-pct">−${fmt(pct, 0)}% CO₂</span>
      <span class="muted">${fmt(b.ghg, 1)} → ${fmt(a.ghg, 1)} kg for the whole recipe${saved > 0.5 ? ` · about ${fmt(saved / 0.4, 0)} miles of driving` : ""}</span>
    </div>` : "";

  const nutri = r.nutrient_flags.length ? `
    <div class="note nutri"><h3>Nutrients to watch <span class="muted small">(not medical advice)</span></h3><ul>
      ${r.nutrient_flags.map((n) => `<li><strong>${esc(n.nutrient)}</strong> (was in ${esc(n.lost_from.join(", "))}): ${esc(n.tip)}</li>`).join("")}
    </ul></div>` : "";
  const warns = r.warnings.length ? `
    <div class="note warn"><h3>Check these</h3><ul>
      ${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}
    </ul></div>` : "";

  el.innerHTML = `
    <div class="card">
      <div class="result-head"><h2>${esc(r.title)}</h2></div>
      <div class="badges">
        ${cuisine ? `<span class="badge cuisine">${esc(pretty(cuisine))} cuisine</span>` : ""}
        <span class="badge">${esc(r.mode)}</span>
        ${pantryUsed ? `<span class="badge pantry">${pantryUsed} swap${pantryUsed > 1 ? "s" : ""} from your pantry</span>` : ""}
      </div>
      <p class="recipe-kicker">${r.swaps.length} swap${r.swaps.length === 1 ? "" : "s"}, highest impact first. Tap one to see why.</p>
      <div class="swaps">${swaps}</div>
      ${impact}
    </div>
    ${r.swaps.length ? `<div class="card map-card">
      <div class="row-between"><h3 class="section-title">Why these swaps? <span class="muted small">Epicure's flavor map</span></h3>
        <button class="link small" id="mapZoom">Show whole map</button></div>
      <div class="map-wrap"><svg id="flavorMap" role="img" aria-label="Map of ingredients; similar ingredients sit close together"></svg></div>
      <p class="why" id="whyText"></p>
      <p class="fineprint">Each dot is one of 1,790 ingredients, placed so that ingredients used in similar recipes sit close together (t-SNE of Epicure embeddings, learned from about 4 million recipes). Swaps are scored on the full 300-dimension embedding, not this 2D picture.</p>
    </div>` : ""}
    ${nutri || warns ? `<div class="card notes">${nutri}${warns}</div>` : ""}
    <p class="fineprint">CO₂ uses global averages (Poore &amp; Nemecek 2018); data covers ${fmt(b.coverage * 100, 0)}% of this recipe by weight. Driving comparison uses the US EPA estimate of about 0.4 kg CO₂ per mile.</p>`;

  el.querySelectorAll(".alt").forEach((btn) =>
    btn.addEventListener("click", (ev) => { ev.stopPropagation(); state.overrides[btn.dataset.from] = btn.dataset.to; doRemix(); }));
  el.querySelectorAll(".swap[data-i]").forEach((card) =>
    card.addEventListener("click", () => {
      el.querySelectorAll(".swap").forEach((c) => c.classList.toggle("selected", c === card));
      drawMap(r, +card.dataset.i);
      const map = document.querySelector(".map-card");
      const box = map?.getBoundingClientRect();
      if (box && (box.top > window.innerHeight * 0.6 || box.bottom < 0)) map.scrollIntoView({ behavior: "smooth", block: "center" });
    }));
  if (r.swaps.length) {
    $("#mapZoom").addEventListener("click", () => {
      mapState.zoomed = !mapState.zoomed;
      $("#mapZoom").textContent = mapState.zoomed ? "Show whole map" : "Zoom to dish";
      drawMap(r, mapState.selected);
    });
    $("#mapZoom").textContent = mapState.zoomed ? "Show whole map" : "Zoom to dish";
    drawMap(r, 0);
  }
  renderPantry();
  if (window.innerWidth < 920 && !renderResult._scrolled) {
    renderResult._scrolled = true;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}


// ---------- flavor map ----------
const mapState = { data: null, index: null, zoomed: true, selected: 0 };
async function getMap() {
  if (!mapState.data) {
    mapState.data = await api("/api/flavor-map");
    mapState.index = Object.fromEntries(mapState.data.points.map((p) => [p.n, p]));
  }
  return mapState.data;
}
const SVGNS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs, text) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text != null) n.textContent = text;
  return n;
}

async function drawMap(r, sel) {
  const svg = $("#flavorMap");
  if (!svg) return;
  const data = await getMap();
  mapState.selected = sel;
  const W = 1000, H = 700, P = 30;
  const X = (p) => P + p.x * (W - 2 * P);
  const Y = (p) => P + (1 - p.y) * (H - 2 * P);
  const at = (n) => mapState.index[n];

  // Points we care about
  const dish = r.dish_epicure.map(at).filter(Boolean);
  const swaps = r.swaps.map((s, i) => ({ i, s, from: at(s.from_epicure), to: at(s.to) })).filter((o) => o.from && o.to);
  const cur = swaps.find((o) => o.i === sel);
  const whyNames = new Set((r.swaps[sel]?.why || []).map((w) => w.name));
  // Zoom to the story of the selected swap: where it came from, where it went, and why.
  const focus = cur ? [cur.from, cur.to, ...[...whyNames].map(at).filter(Boolean)] : dish;

  // viewBox: zoom to the dish (padded), or whole map
  let vb = [0, 0, W, H];
  if (mapState.zoomed && focus.length) {
    const xs = focus.map(X), ys = focus.map(Y);
    let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const pad = 90;
    x0 -= pad; x1 += pad; y0 -= pad; y1 += pad;
    // keep the map's aspect ratio
    const w = x1 - x0, h = y1 - y0, ar = W / H;
    if (w / h > ar) { const nh = w / ar; y0 -= (nh - h) / 2; y1 = y0 + nh; } else { const nw = h * ar; x0 -= (nw - w) / 2; x1 = x0 + nw; }
    vb = [x0, y0, x1 - x0, y1 - y0];
  }
  svg.setAttribute("viewBox", vb.join(" "));
  const k = vb[2] / W; // scale so dots/labels keep a constant on-screen size
  svg.replaceChildren();

  const g = svgEl("g", {});
  svg.append(g);
  // background dots
  for (const p of data.points) g.append(svgEl("circle", { cx: X(p), cy: Y(p), r: 2.4 * k, class: "dot" }));
  // region labels
  for (const reg of data.regions)
    g.append(svgEl("text", { x: X(reg), y: Y(reg), class: "region", "font-size": 30 * k, "text-anchor": "middle" }, reg.name));
  // dish ingredients
  for (const p of dish) {
    const w = whyNames.has(p.n);
    g.append(svgEl("circle", { cx: X(p), cy: Y(p), r: (w ? 6 : 4.5) * k, class: `dish-dot ${w ? "why-dot" : ""}` }));
    g.append(svgEl("text", { x: X(p) + 9 * k, y: Y(p) + 5 * k, class: `dish-label ${w ? "why-label" : ""}`, "font-size": (w ? 17 : 14) * k }, pretty(p.n)));
  }
  // swap arrows
  const defs = svgEl("defs", {});
  const mk = svgEl("marker", { id: "arrow", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" });
  mk.append(svgEl("path", { d: "M0,0 L10,5 L0,10 z", class: "arrow-head" }));
  defs.append(mk);
  svg.prepend(defs);
  for (const o of swaps) {
    const on = o.i === sel;
    const x1 = X(o.from), y1 = Y(o.from), x2 = X(o.to), y2 = Y(o.to);
    const mx = (x1 + x2) / 2 - (y2 - y1) * 0.2, my = (y1 + y2) / 2 + (x2 - x1) * 0.2;
    const path = svgEl("path", { d: `M${x1},${y1} Q${mx},${my} ${x2},${y2}`, class: `swap-arrow ${on ? "on" : ""}`,
      "stroke-width": (on ? 3 : 1.5) * k, "marker-end": "url(#arrow)" });
    g.append(path);
    if (on) {
      const len = path.getTotalLength();
      path.style.strokeDasharray = len;
      path.style.strokeDashoffset = len;
      requestAnimationFrame(() => { path.style.transition = "stroke-dashoffset .9s ease"; path.style.strokeDashoffset = 0; });
    }
    g.append(svgEl("circle", { cx: x1, cy: y1, r: (on ? 7 : 5) * k, class: `from-dot ${on ? "on" : ""}` }));
    g.append(svgEl("circle", { cx: x2, cy: y2, r: (on ? 9 : 6) * k, class: `to-dot ${on ? "on" : ""}` }));
    if (on) {
      g.append(svgEl("text", { x: x1 + 10 * k, y: y1 - 8 * k, class: "from-label", "font-size": 18 * k }, pretty(o.s.from_epicure)));
      g.append(svgEl("text", { x: x2 + 12 * k, y: y2 + 6 * k, class: "to-label", "font-size": 22 * k }, pretty(o.s.to)));
    }
  }

  const s = r.swaps[sel];
  const why = (s.why || []).map((w) => `<strong>${esc(pretty(w.name))}</strong>`);
  const list = why.length > 1 ? `${why.slice(0, -1).join(", ")} and ${why[why.length - 1]}` : why.join("");
  $("#whyText").innerHTML = s ? `<span class="to-word">${esc(pretty(s.to))}</span> replaces ${esc(s.from)} because Epicure links it closely with ${list}, which are already in your dish.${
    r.cuisine_lock && r.cuisine?.[0] ? ` It also leans ${esc(pretty(r.cuisine[0][0]))}, like the rest of the dish.` : ""}` : "";
}

// ---------- accuracy card ----------
async function loadBenchmark() {
  const all = await api("/api/benchmark");
  const r = all.core;
  const rows = [
    ["Recipe Remix", r.summary.ours_cuisine_lock, "ours"],
    ["Closest match to the meat", r.summary.nearest_to_meat, ""],
    ['"Just use tofu"', r.summary.always_tofu, ""],
    ["Random pick", r.summary.random, ""],
  ];
  const misses = r.rows.filter((x) => !x.hit1);
  $("#bench").innerHTML = `
    <h3 class="section-title">How accurate is it?</h3>
    <p class="muted small">We wrote down the plant protein used by the well-known plant-based version of ${r.n_dishes} meat dishes across 7 cuisines (chana masala for chicken curry, bean tacos, jackfruit pulled pork…) <em>before</em> testing, then checked how often each method picks it first.</p>
    <div class="bench-bars">
      ${rows.map(([label, v, cls]) => `
        <div class="bench-row ${cls}">
          <span class="bench-label">${label}</span>
          <div class="track"><div class="fill" data-w="${v.hit_at_1 * 100}"></div></div>
          <span class="bench-val">${fmt(v.hit_at_1 * 100, 0)}%</span>
        </div>`).join("")}
    </div>
    <details class="bench-details"><summary>See all ${r.n_dishes} dishes (${misses.length} misses)</summary>
      <ul>${r.rows.map((x) => `<li>${x.hit1 ? "✓" : "✗"} <strong>${esc(x.dish)}</strong>: picked ${esc(pretty(x.ours_top3[0]))}${x.hit1 ? "" : ` (expected ${esc(x.gold.map(pretty).join(" or "))})`}</li>`).join("")}</ul>
      <p class="muted small">Small test set, labelled by us. A sanity check, not a published benchmark.</p>
    </details>`;
  requestAnimationFrame(() => requestAnimationFrame(() =>
    document.querySelectorAll("#bench .fill").forEach((f) => { f.style.width = `${f.dataset.w}%`; })));
}

loadBenchmark().catch(() => $("#bench").classList.add("hidden"));
loadSamples().catch((e) => toast(e.message));
