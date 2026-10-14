import { describe, expect, it } from "vitest";

import { CENTER, RINGS, cellAngles, polar, sectorPath, tokenPoint } from "./geometry";

const dist = (p: { x: number; y: number }) => Math.hypot(p.x - CENTER, p.y - CENTER);

describe("геометрия поля", () => {
  it("кольца не пересекаются, скоростная дорожка снаружи", () => {
    expect(RINGS.fast_track.inner).toBeGreaterThan(RINGS.rat_race.outer);
    expect(RINGS.fast_track.outer).toBeLessThanOrEqual(CENTER);
  });

  it("угол 0 — верх, 90 — справа", () => {
    expect(polar(100, 0).x).toBeCloseTo(CENTER);
    expect(polar(100, 0).y).toBeCloseTo(CENTER - 100);
    expect(polar(100, 90).x).toBeCloseTo(CENTER + 100);
  });

  it("клетки покрывают круг без зазоров", () => {
    expect(cellAngles(0, 24)).toEqual([0, 15]);
    expect(cellAngles(23, 24)[1]).toBeCloseTo(360);
  });

  it("контур клетки замкнут", () => {
    expect(sectorPath(RINGS.rat_race, 3, 24)).toMatch(/^M .* Z$/);
  });

  it("одиночная фишка стоит в середине кольца", () => {
    const p = tokenPoint("rat_race", 5, 24);
    const ring = RINGS.rat_race;
    expect(dist(p)).toBeCloseTo((ring.inner + ring.outer) / 2);
  });

  it("6 фишек на одной клетке не совпадают и остаются в кольце", () => {
    const ring = RINGS.fast_track;
    const points = Array.from({ length: 6 }, (_, i) => tokenPoint("fast_track", 7, 40, i, 6));
    const keys = new Set(points.map((p) => `${p.x.toFixed(1)}:${p.y.toFixed(1)}`));
    expect(keys.size).toBe(6);
    for (const p of points) {
      expect(dist(p)).toBeGreaterThan(ring.inner - 25);
      expect(dist(p)).toBeLessThan(ring.outer + 25);
    }
  });
});
