import { useEffect, useState } from "react";

import type { Track } from "../../api/types";
import { moveFor } from "../../lib/movement";
import { STEP_MS } from "../../lib/timing";
import { onGameEvent } from "../../store/game";

export interface Spot {
  track: Track;
  position: number;
}

/**
 * Пошаговое движение фишек. Сервер сразу присылает конечную позицию,
 * а здесь фишка стоит на старте, пока падают кубики, и «шагает» по клеткам
 * по расписанию из lib/movement. Возвращает позиции, которые нужно показывать
 * вместо настоящих, пока идёт анимация.
 */
export function useTokenSteps() {
  const [overrides, setOverrides] = useState<Record<number, Spot>>({});

  useEffect(() => {
    const timers: number[] = [];
    const at = (time: number, fn: () => void) =>
      timers.push(window.setTimeout(fn, Math.max(0, time - Date.now())));

    const unsubscribe = onGameEvent((event) => {
      const move = event.kind === "moved" ? moveFor(event.seq) : undefined;
      if (!move) return;
      const { playerId, track, start, path, startAt } = move;
      const show = (position: number) => setOverrides((o) => ({ ...o, [playerId]: { track, position } }));

      // Держим фишку на старте, пока падают кубики. Если она ещё идёт
      // предыдущий ход, то сама придёт на старт этого.
      if (!move.queued) show(start);
      path.forEach((position, i) => at(startAt + i * STEP_MS, () => show(position)));
      at(move.arrival, () =>
        setOverrides((o) => {
          // Если за это время начался ещё один ход — не трогаем.
          if (o[playerId]?.position !== path[path.length - 1]) return o;
          const { [playerId]: _, ...rest } = o;
          return rest;
        }),
      );
    });

    return () => {
      unsubscribe();
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, []);

  return overrides;
}
