// Pixel-art sprites, drawn as crisp SVG rectangles. Each row is one line of pixels;
// each letter is a colour from PALETTE ("." is transparent).
const PALETTE = {
  k: "#2b2433", // outline
  g: "#5cc97b", G: "#2f8f52", l: "#b8f0a8", // greens
  y: "#ffd65a", o: "#f6923a", r: "#ef5d5d", // warm
  b: "#b8743f", B: "#7a4a26",               // browns
  w: "#fffaf0", s: "#c9c1d6", p: "#ff9ecb", // white, grey, pink
  u: "#7fcff7", U: "#3d86d6",               // blues
};

const SPRITES = {
  sprout: [
    "................",
    "...kkk....kkk...",
    "..kllk...kgggk..",
    ".klllk..kggggk..",
    ".kllllk.kgggk...",
    "..kllllkkggk....",
    "...klllkgkk.....",
    "....kkkkgk......",
    ".......kgk......",
    ".......kgk......",
    ".......kgk......",
    "....kkkkkkkk....",
    "...kbbbbbbbbk...",
    "...kBbbbbbbBk...",
    "....kBBBBBBk....",
    ".....kkkkkk.....",
  ],
  curry: [
    "................",
    "....s...s...s...",
    ".....s...s...s..",
    "....s...s...s...",
    "................",
    ".kkkkkkkkkkkkkk.",
    "kwwwwwooooogoook",
    "kwwwwooroooooook",
    ".kkkkkkkkkkkkkk.",
    ".kuuuuuuuuuuuuk.",
    "..kuuuuuuuuuuk..",
    "...kkkkkkkkkk...",
    "....kUUUUUUk....",
    "....kkkkkkkk....",
    "................",
    "................",
  ],
  taco: [
    "................",
    "................",
    "................",
    "......kkkk......",
    "....kkgrglkk....",
    "...kgrlgrglgk...",
    "..kyklgrbbrgyk..",
    ".kyyybbbbbbbyyk.",
    ".kyyyyyyyyyyyyk.",
    "kyyyyyyyyyyyyyyk",
    "kyyyyyyyyyyyyyyk",
    ".kkkkkkkkkkkkkk.",
    "................",
    "................",
    "................",
    "................",
  ],
  pasta: [
    "................",
    "................",
    "......kkkk......",
    "....kkrrrrkk....",
    "...kyyrrrryyk...",
    "..kyyyyrryyyyk..",
    "..kyyyyyyyygyk..",
    ".kkkkkkkkkkkkkk.",
    "kwwwwwwwwwwwwwwk",
    ".kwwwwwwwwwwwwk.",
    "..kkkkkkkkkkkk..",
    "................",
    "................",
    "................",
    "................",
    "................",
  ],
  bowl: [
    "..............B.",
    ".............B..",
    "............B...",
    "...........B....",
    "..........B.....",
    ".kkkkkkkkkkkkkk.",
    "krwwrwwrrwwrwwrk",
    "krrwwrrwwrrwwrrk",
    ".kkkkkkkkkkkkkk.",
    ".kwuwuwuwuwuwuk.",
    "..kwwwwwwwwwwk..",
    "...kkkkkkkkkk...",
    "....kssssssk....",
    "....kkkkkkkk....",
    "................",
    "................",
  ],
  can: [
    "................",
    "....kkkkkkkk....",
    "...kssssssssk...",
    "...kkkkkkkkkk...",
    "...kggggggggk...",
    "...kgwwwwwwgk...",
    "...kgwyyyywgk...",
    "...kgwyyyywgk...",
    "...kgwwwwwwgk...",
    "...kggggggggk...",
    "...kkkkkkkkkk...",
    "...kssssssssk...",
    "....kkkkkkkk....",
    "................",
    "................",
    "................",
  ],
  camera: [
    "................",
    "................",
    "................",
    "......kkkk......",
    "..kkkkkuukkkkk..",
    ".kppppkkkkppwpk.",
    ".kppkkuuuukkppk.",
    ".kppkuuwuuukppk.",
    ".kppkuuuuuukppk.",
    ".kppkkuuuukkppk.",
    ".kppppkkkkppppk.",
    ".kkkkkkkkkkkkkk.",
    "................",
    "................",
    "................",
    "................",
  ],
  sparkle: [
    "...y...",
    "...y...",
    ".yyyyy.",
    "...y...",
    "...y...",
    ".......",
  ],
};

// Returns an <svg> string; size is the rendered width in CSS pixels.
function sprite(name, size = 32, title = "") {
  const rows = SPRITES[name];
  if (!rows) return "";
  const h = rows.length, w = rows[0].length;
  let rects = "";
  rows.forEach((row, y) => {
    // merge runs of the same colour into one rect
    let x = 0;
    while (x < w) {
      const c = row[x];
      let run = 1;
      while (x + run < w && row[x + run] === c) run++;
      if (c !== ".") rects += `<rect x="${x}" y="${y}" width="${run}" height="1" fill="${PALETTE[c]}"/>`;
      x += run;
    }
  });
  const label = title ? `role="img" aria-label="${title}"` : 'aria-hidden="true"';
  return `<svg class="px" ${label} viewBox="0 0 ${w} ${h}" width="${size}" height="${Math.round(size * h / w)}" shape-rendering="crispEdges">${rects}</svg>`;
}
