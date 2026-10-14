import { describe, expect, it } from "vitest";

import { effectiveVolume } from "./sound";

const settings = {
  muted: false,
  master: 0.5,
  groups: { dice: 0.2, steps: 1, money: 1, cards: 1, signals: 1 },
};

describe("громкость", () => {
  it("умножается: базовая × группа × общая", () => {
    expect(effectiveVolume("dice-3", 0.6, settings)).toBeCloseTo(0.06);
    expect(effectiveVolume("coins-in", 0.6, settings)).toBeCloseTo(0.3);
  });

  it("выключенный звук — тишина", () => {
    expect(effectiveVolume("coins-in", 0.6, { ...settings, muted: true })).toBe(0);
  });

  it("не больше 1", () => {
    expect(effectiveVolume("win", 3, { ...settings, master: 1 })).toBe(1);
  });
});
