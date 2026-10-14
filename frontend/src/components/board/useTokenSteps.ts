import { useEffect, useRef, useState } from "react";

import type { Track } from "../../api/types";
import { onGameEvent } from "../../store/game";

export const STEP_MS = 280;

export interface Spot {
  track: Track;
  position: number;
}

interface MovedPayload {
  track: Track;
  start: number;
  path: number[];
}

/**
 * Пошаговое движение фишек. Сервер сразу присылает конечную позицию,
 * а здесь фишка «шагает» по клеткам из события moved.
 * Возвращает позиции, которые нужно показывать вместо настоящих, пока идёт анимация,
 * и функцию: через сколько мс фишка игрока дойдёт до конца.
 */
export function useTokenSteps() {
  const [overrides, setOverrides] = useState<Record<number, Spot>>({});
  const queues = useRef(new Map<number, Spot[]>());
  const timers = useRef(new Map<number, number>());

  useEffect(() => {
    const tick = (playerId: number) => {
      const queue = queues.current.get(playerId) ?? [];
      const next = queue.shift();
      if (!next) {
        window.clearInterval(timers.current.get(playerId));
        timers.current.delete(playerId);
        setOverrides(({ [playerId]: _, ...rest }) => rest);
        return;
      }
      setOverrides((o) => ({ ...o, [playerId]: next }));
    };

    const unsubscribe = onGameEvent((event) => {
      if (event.kind !== "moved" || event.player_id == null) return;
      const { track, start, path } = event.payload as unknown as MovedPayload;
      const playerId = event.player_id;
      const queue = queues.current.get(playerId) ?? [];
      if (!timers.current.has(playerId)) {
        // Держим фишку на старте, пока не начнётся анимация.
        setOverrides((o) => ({ ...o, [playerId]: { track, position: start } }));
        timers.current.set(
          playerId,
          window.setInterval(() => tick(playerId), STEP_MS),
        );
      }
      queues.current.set(playerId, [...queue, ...path.map((position) => ({ track, position }))]);
    });

    const activeTimers = timers.current;
    return () => {
      unsubscribe();
      activeTimers.forEach((t) => window.clearInterval(t));
      activeTimers.clear();
    };
  }, []);

  const remainingMs = (playerId: number) =>
    ((queues.current.get(playerId)?.length ?? 0) + 1) * STEP_MS;

  return { overrides, remainingMs };
}
