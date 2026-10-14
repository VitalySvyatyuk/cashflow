import type { Track } from "../../api/types";

/** Поле рисуется в квадрате 1000×1000, центр — (500, 500). */
export const SIZE = 1000;
export const CENTER = SIZE / 2;

export interface Ring {
  inner: number;
  outer: number;
}

// Скоростная дорожка охватывает крысиные бега.
export const RINGS: Record<Track, Ring> = {
  fast_track: { inner: 415, outer: 495 },
  rat_race: { inner: 255, outer: 345 },
};

export const TOKEN_RADIUS = 14;
const TOKEN_GAP = 30;
const TOKENS_PER_ROW = 3;

export interface Point {
  x: number;
  y: number;
}

/** Точка на окружности; угол в градусах от «12 часов» по часовой стрелке. */
export function polar(radius: number, degrees: number): Point {
  const rad = (degrees * Math.PI) / 180;
  return { x: CENTER + radius * Math.sin(rad), y: CENTER - radius * Math.cos(rad) };
}

export function cellAngles(position: number, count: number): [number, number] {
  const step = 360 / count;
  return [position * step, (position + 1) * step];
}

/** Контур клетки — сектор кольца. */
export function sectorPath(ring: Ring, position: number, count: number): string {
  const [a0, a1] = cellAngles(position, count);
  const large = a1 - a0 > 180 ? 1 : 0;
  const o0 = polar(ring.outer, a0);
  const o1 = polar(ring.outer, a1);
  const i1 = polar(ring.inner, a1);
  const i0 = polar(ring.inner, a0);
  const f = (n: number) => n.toFixed(2);
  return [
    `M ${f(o0.x)} ${f(o0.y)}`,
    `A ${ring.outer} ${ring.outer} 0 ${large} 1 ${f(o1.x)} ${f(o1.y)}`,
    `L ${f(i1.x)} ${f(i1.y)}`,
    `A ${ring.inner} ${ring.inner} 0 ${large} 0 ${f(i0.x)} ${f(i0.y)}`,
    "Z",
  ].join(" ");
}

/**
 * Где стоит фишка: центр клетки, а если на клетке несколько фишек —
 * раскладываем их сеткой по 3 в ряд вдоль кольца.
 */
export function tokenPoint(
  track: Track,
  position: number,
  count: number,
  index = 0,
  together = 1,
): Point {
  const ring = RINGS[track];
  const [a0, a1] = cellAngles(position, count);
  const angle = (a0 + a1) / 2;
  const radius = (ring.inner + ring.outer) / 2;

  const cols = Math.min(together, TOKENS_PER_ROW);
  const rows = Math.ceil(together / TOKENS_PER_ROW);
  const col = index % TOKENS_PER_ROW;
  const row = Math.floor(index / TOKENS_PER_ROW);
  const along = (col - (cols - 1) / 2) * TOKEN_GAP; // вдоль кольца
  const across = ((rows - 1) / 2 - row) * TOKEN_GAP; // наружу/внутрь

  const rad = (angle * Math.PI) / 180;
  const base = polar(radius + across, angle);
  return { x: base.x + along * Math.cos(rad), y: base.y + along * Math.sin(rad) };
}
