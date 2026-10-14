import { motion } from "motion/react";
import { useEffect, useState } from "react";

import { DICE_MS } from "../../lib/timing";
import { onGameEvent } from "../../store/game";

/**
 * Как повернуть кубик, чтобы к нам смотрела грань с этим числом.
 * Грани: 1 спереди, 6 сзади, 2 справа, 5 слева, 3 сверху, 4 снизу
 * (противоположные в сумме дают 7, как у настоящего кубика).
 */
export const FACE_ROTATION: Record<number, [number, number]> = {
  1: [0, 0],
  6: [0, 180],
  2: [0, -90],
  5: [0, 90],
  3: [-90, 0],
  4: [90, 0],
};

const FACES: { value: number; transform: string }[] = [
  { value: 1, transform: "rotateY(0deg)" },
  { value: 6, transform: "rotateY(180deg)" },
  { value: 2, transform: "rotateY(90deg)" },
  { value: 5, transform: "rotateY(-90deg)" },
  { value: 3, transform: "rotateX(90deg)" },
  { value: 4, transform: "rotateX(-90deg)" },
];

// Где точки на грани: номера ячеек сетки 3×3.
const PIPS: Record<number, number[]> = {
  1: [4],
  2: [2, 6],
  3: [2, 4, 6],
  4: [0, 2, 6, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 3, 5, 6, 8],
};

// Траектория броска: прилетает сбоку, бьётся о стол и затихает.
const BOUNCE_TIMES = [0, 0.38, 0.56, 0.72, 0.84, 0.93, 1];
const HEIGHTS = [-150, 0, -48, 0, -16, 0, 0];
const SHADOW_SCALE = [0.35, 1, 0.75, 1, 0.92, 1, 1];

/** Кубики в центре поля. Кувыркаются, когда приходит событие броска. */
export function Dice({ values }: { values: number[] }) {
  const [rollKey, setRollKey] = useState(0);
  useEffect(
    () =>
      onGameEvent((event) => {
        if (event.kind === "dice_rolled") setRollKey(event.seq);
      }),
    [],
  );

  if (!values.length) return null;
  return (
    <div className="dice-row" aria-label={`Выпало: ${values.join(", ")}`}>
      {values.map((value, i) => (
        <Die
          key={`${rollKey}-${i}`}
          value={value}
          index={i}
          count={values.length}
          animate={rollKey > 0}
        />
      ))}
    </div>
  );
}

interface Throw {
  fromX: number;
  spinX: number;
  spinY: number;
  twistFrom: number;
  tilt: number;
}

function randomThrow(index: number, count: number): Throw {
  const rand = (min: number, max: number) => min + Math.random() * (max - min);
  // Кубики летят из одной руки: крайние — чуть дальше по горизонтали.
  const side = index - (count - 1) / 2;
  return {
    fromX: -170 + side * 30 + rand(-20, 20),
    spinX: 360 * Math.round(rand(2, 4)),
    spinY: 360 * Math.round(rand(1, 3)) * (Math.random() < 0.5 ? -1 : 1),
    twistFrom: rand(-220, 220),
    tilt: rand(-14, 14),
  };
}

function Die(props: { value: number; index: number; count: number; animate: boolean }) {
  const { value, index, count, animate } = props;
  const [throwParams] = useState(() => randomThrow(index, count));
  const { fromX, spinX, spinY, twistFrom, tilt } = throwParams;
  const [x, y] = FACE_ROTATION[value];
  const duration = DICE_MS / 1000;
  const delay = index * 0.07;

  // Без анимации (например, после перезагрузки страницы) — сразу в покое.
  const from = <T,>(value: T) => (animate ? value : false);

  return (
    <div className="die-slot">
      <motion.div
        className="die-shadow"
        initial={from({ scaleX: SHADOW_SCALE[0], opacity: 0, x: fromX })}
        animate={{ scaleX: SHADOW_SCALE, opacity: 1, x: 0 }}
        transition={{
          scaleX: { duration, delay, times: BOUNCE_TIMES },
          opacity: { duration: 0.2, delay },
          x: { duration: duration * 0.8, delay, ease: "easeOut" },
        }}
      />
      {/* Внешний слой: полёт, отскоки и поворот в плоскости стола */}
      <motion.div
        className="die-flight"
        initial={from({ x: fromX, y: HEIGHTS[0], rotateZ: twistFrom, opacity: 0 })}
        animate={{ x: 0, y: HEIGHTS, rotateZ: tilt, opacity: 1 }}
        transition={{
          delay,
          x: { duration: duration * 0.8, delay, ease: [0.15, 0.6, 0.3, 1] },
          y: { duration, delay, times: BOUNCE_TIMES, ease: "easeOut" },
          rotateZ: { duration: duration * 0.9, delay, ease: [0.1, 0.7, 0.3, 1] },
          opacity: { duration: 0.12, delay },
        }}
      >
        {/* Внутренний слой: кувыркание; заканчивает ровно на нужной грани */}
        <motion.div
          className="die"
          initial={from({ rotateX: x - spinX, rotateY: y - spinY })}
          animate={{ rotateX: x, rotateY: y }}
          transition={{ duration: duration * 0.92, delay, ease: [0.12, 0.65, 0.25, 1] }}
        >
          {/* Внутренние плоскости закрывают щели на скруглённых рёбрах */}
          <div className="die-core" />
          <div className="die-core" style={{ transform: "rotateX(90deg)" }} />
          <div className="die-core" style={{ transform: "rotateY(90deg)" }} />
          {FACES.map((face) => (
            <div
              key={face.value}
              className={`die-face face-${face.value}`}
              style={{ transform: `${face.transform} translateZ(var(--die-half))` }}
            >
              {Array.from({ length: 9 }, (_, cell) => (
                <span key={cell} className={PIPS[face.value].includes(cell) ? "pip" : ""} />
              ))}
            </div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
