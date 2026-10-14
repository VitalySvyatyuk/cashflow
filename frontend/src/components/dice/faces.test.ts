import { describe, expect, it } from "vitest";

import { FACE_ROTATION } from "./Dice";

// Поворачиваем нормаль грани (как в CSS: ось Y вниз) и проверяем, что она смотрит на нас.
type Vec = [number, number, number];
const rad = (d: number) => (d * Math.PI) / 180;
const rotX = ([x, y, z]: Vec, a: number): Vec => [
  x,
  y * Math.cos(rad(a)) - z * Math.sin(rad(a)),
  y * Math.sin(rad(a)) + z * Math.cos(rad(a)),
];
const rotY = ([x, y, z]: Vec, a: number): Vec => [
  x * Math.cos(rad(a)) + z * Math.sin(rad(a)),
  y,
  -x * Math.sin(rad(a)) + z * Math.cos(rad(a)),
];

// Нормали граней так, как они расставлены в Dice.tsx.
const NORMALS: Record<number, Vec> = {
  1: [0, 0, 1],
  6: rotY([0, 0, 1], 180),
  2: rotY([0, 0, 1], 90),
  5: rotY([0, 0, 1], -90),
  3: rotX([0, 0, 1], 90),
  4: rotX([0, 0, 1], -90),
};

describe("кубик", () => {
  it.each([1, 2, 3, 4, 5, 6])("поворот для %i показывает эту грань", (value) => {
    const [ax, ay] = FACE_ROTATION[value];
    // motion применяет rotateX, затем rotateY: в матрице сначала действует rotateY
    const facing = rotX(rotY(NORMALS[value], ay), ax);
    expect(facing[2]).toBeCloseTo(1);
  });

  it("противоположные грани в сумме 7", () => {
    for (const v of [1, 2, 3]) {
      const n = NORMALS[v];
      const opposite = NORMALS[7 - v];
      expect(n[0] + opposite[0]).toBeCloseTo(0);
      expect(n[1] + opposite[1]).toBeCloseTo(0);
      expect(n[2] + opposite[2]).toBeCloseTo(0);
    }
  });
});
