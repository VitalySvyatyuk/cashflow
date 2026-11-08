// Рисует игровое поле для лендинга (public/cashflow/board.svg) — те же кольца, цвета клеток
// и значки, что в игре (components/board), плюс несколько фишек. Клетки берутся из API.
//
//   node scripts/render-landing-board.mjs [https://emelyanova-play.ru]
//
// Шрифт названия вшит в SVG: картинка в <img> не может подгрузить внешний шрифт.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = process.argv[2] ?? "https://emelyanova-play.ru";

// Значки и геометрия — копия icons.ts / geometry.ts (TypeScript отсюда не импортировать).
const iconsSrc = readFileSync(join(root, "src/components/board/icons.ts"), "utf8");
const PATHS = Object.fromEntries(
  [...iconsSrc.matchAll(/^\s+(\w+): "(M[^"]+)"/gm)].map((m) => [m[1], m[2]]),
);
const CELL_ICONS = {
  paycheck: PATHS.ruble,
  cashflow_day: PATHS.ruble,
  charity: PATHS.charity,
  market: PATHS.tv,
  doodad: PATHS.shop,
  baby: PATHS.baby,
  downsized: PATHS.workOff,
  dream: PATHS.star,
  loss: PATHS.trendingDown,
};
const ICON_SIZE = { rat_race: 38, fast_track: 30 };
const RINGS = { fast_track: { inner: 415, outer: 495 }, rat_race: { inner: 255, outer: 345 } };
const C = 500;
const f = (n) => n.toFixed(2);

function polar(r, deg) {
  const a = (deg * Math.PI) / 180;
  return { x: C + r * Math.sin(a), y: C - r * Math.cos(a) };
}
function sector(ring, pos, count) {
  const a0 = (pos * 360) / count;
  const a1 = ((pos + 1) * 360) / count;
  const o0 = polar(ring.outer, a0), o1 = polar(ring.outer, a1);
  const i1 = polar(ring.inner, a1), i0 = polar(ring.inner, a0);
  return `M${f(o0.x)} ${f(o0.y)}A${ring.outer} ${ring.outer} 0 0 1 ${f(o1.x)} ${f(o1.y)}L${f(i1.x)} ${f(i1.y)}A${ring.inner} ${ring.inner} 0 0 0 ${f(i0.x)} ${f(i0.y)}Z`;
}
function cellCenter(track, pos, count) {
  const ring = RINGS[track];
  return polar((ring.inner + ring.outer) / 2, ((pos + 0.5) * 360) / count);
}
function ink(hex) {
  const n = parseInt(hex.slice(1), 16);
  const y = 0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255);
  return y > 165 ? "rgba(30,25,10,0.78)" : "rgba(255,255,255,0.93)";
}
function shade(hex, k) {
  const n = parseInt(hex.slice(1), 16);
  return "#" + [n >> 16, (n >> 8) & 255, n & 255]
    .map((v) => Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k).toString(16).padStart(2, "0"))
    .join("");
}

const cells = await (await fetch(`${origin}/api/board/`)).json();
const tracks = {
  fast_track: cells.filter((c) => c.track === "fast_track"),
  rat_race: cells.filter((c) => c.track === "rat_race"),
};

const out = [];
out.push(`<g filter="url(#rs)">`);
for (const [track, list] of Object.entries(tracks)) {
  for (const c of list) out.push(`<path d="${sector(RINGS[track], c.position, list.length)}" fill="${c.color}" stroke="#0f3324" stroke-width="3"/>`);
}
out.push(`</g>`);
for (const [track, list] of Object.entries(tracks)) {
  for (const c of list) {
    const d = CELL_ICONS[c.kind];
    if (!d) continue;
    const { x, y } = cellCenter(track, c.position, list.length);
    const s = ICON_SIZE[track];
    out.push(`<path d="${d}" transform="translate(${f(x - s / 2)} ${f(y + s / 2)}) scale(${(s / 960).toFixed(4)})" fill="${ink(c.color)}"/>`);
  }
}

// Фишки: игроки разбросаны по клеткам без значков (возможности, бизнесы), один — на большом круге.
const PLAYER_COLORS = ["#e53935", "#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00"];
const plain = (track) => tracks[track].filter((c) => !CELL_ICONS[c.kind]).map((c) => c.position);
const rr = plain("rat_race");
const ft = plain("fast_track");
const tokens = [
  ["rat_race", rr[1], 0],
  ["rat_race", rr[Math.floor(rr.length * 0.35)], 1],
  ["rat_race", rr[Math.floor(rr.length * 0.6)], 3],
  ["rat_race", rr[rr.length - 2], 5],
  ["fast_track", ft[Math.floor(ft.length * 0.3)], 2],
];
const defs = PLAYER_COLORS.map((col, i) =>
  `<radialGradient id="t${i}" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="${shade(col, 0.35)}"/><stop offset="0.6" stop-color="${col}"/><stop offset="1" stop-color="${shade(col, -0.35)}"/></radialGradient>`,
).join("");
for (const [track, pos, ci] of tokens) {
  const list = tracks[track];
  const { x, y } = cellCenter(track, pos, list.length);
  out.push(`<g transform="translate(${f(x)} ${f(y)})" filter="url(#ts)"><circle r="17" fill="#fff"/><circle r="14" fill="url(#t${ci})"/><ellipse cx="-4.2" cy="-5.3" rx="7" ry="4.2" fill="#fff" opacity="0.45"/></g>`);
}

const font = readFileSync(join(root, "public/fonts/unbounded-800-cyrillic.woff2")).toString("base64");
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">
<title>Игровое поле «Денежный поток»: крысиные бега и скоростная дорожка</title>
<defs>
<style>@font-face{font-family:U;font-weight:800;src:url(data:font/woff2;base64,${font}) format("woff2")}</style>
<filter id="rs" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="6" stdDeviation="10" flood-opacity="0.5"/></filter>
<filter id="ts" x="-50%" y="-50%" width="200%" height="200%"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-opacity="0.45"/></filter>
${defs}
</defs>
${out.join("\n")}
<circle cx="500" cy="500" r="241" fill="#174a37" stroke="rgba(241,213,138,0.2)" stroke-width="2"/>
<circle cx="500" cy="500" r="221" fill="none" stroke="#f1d58a" stroke-opacity="0.25" stroke-width="1.5" stroke-dasharray="3 7"/>
<text text-anchor="middle" font-family="U, sans-serif" font-size="40" font-weight="800" letter-spacing="2" fill="#f1d58a"><tspan x="500" y="486">ДЕНЕЖНЫЙ</tspan><tspan x="500" y="534">ПОТОК</tspan></text>
</svg>
`;
const target = join(root, "public/cashflow/board.svg");
writeFileSync(target, svg);
console.log(`${target}: ${cells.length} клеток, ${(svg.length / 1024).toFixed(1)} КБ`);
