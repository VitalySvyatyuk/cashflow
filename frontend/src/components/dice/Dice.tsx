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
  2: [0, 8],
  3: [0, 4, 8],
  4: [0, 2, 6, 8],
  5: [0, 2, 4, 6, 8],
  6: [0, 2, 3, 5, 6, 8],
};

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
        <Die key={`${rollKey}-${i}`} value={value} index={i} animate={rollKey > 0} />
      ))}
    </div>
  );
}

function Die({ value, index, animate }: { value: number; index: number; animate: boolean }) {
  const [x, y] = FACE_ROTATION[value];
  // Каждый кубик крутится по-своему, но заканчивает ровно на нужной грани.
  const [spinX] = useState(() => 360 * (2 + Math.floor(Math.random() * 2)));
  const [spinY] = useState(() => 360 * (1 + Math.floor(Math.random() * 2)));
  const seconds = DICE_MS / 1000;

  return (
    <motion.div
      className="die"
      initial={
        animate
          ? { rotateX: x - spinX, rotateY: y - spinY, y: -160, opacity: 0, scale: 0.7 }
          : false
      }
      animate={{ rotateX: x, rotateY: y, y: 0, opacity: 1, scale: 1 }}
      transition={{
        rotateX: { duration: seconds, ease: [0.2, 0.7, 0.3, 1] },
        rotateY: { duration: seconds, ease: [0.2, 0.7, 0.3, 1] },
        y: { type: "spring", duration: seconds * 0.85, bounce: 0.45 },
        opacity: { duration: 0.15 },
        scale: { duration: seconds * 0.6 },
        delay: index * 0.06,
      }}
    >
      {FACES.map((face) => (
        <div key={face.value} className="die-face" style={{ transform: `${face.transform} translateZ(var(--die-half))` }}>
          {Array.from({ length: 9 }, (_, cell) => (
            <span key={cell} className={PIPS[face.value].includes(cell) ? "pip" : "pip-empty"} />
          ))}
        </div>
      ))}
    </motion.div>
  );
}
