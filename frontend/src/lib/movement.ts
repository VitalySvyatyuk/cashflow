import type { GameEvent, Track } from "../api/types";
import { DICE_MS, STEP_MS } from "./timing";

export interface Move {
  playerId: number;
  track: Track;
  start: number;
  path: number[];
  /** Когда фишка делает первый шаг и когда приходит на место (Date.now()). */
  startAt: number;
  arrival: number;
  /** Фишка ещё идёт предыдущий ход — этот начнётся после него. */
  queued: boolean;
}

const moves = new Map<number, Move>(); // seq события → ход
const arrivals = new Map<number, number>(); // игрок → когда закончит идти

/**
 * Расписание хода по событию moved. Фишка ждёт, пока упадут кубики,
 * и не начинает новый ход, пока не закончила предыдущий.
 */
export function recordMove(event: GameEvent, now = Date.now()): Move | null {
  if (event.kind !== "moved" || event.player_id == null) return null;
  const { track, start, path } = event.payload as unknown as {
    track: Track;
    start: number;
    path: number[];
  };
  const previous = arrivals.get(event.player_id) ?? 0;
  const startAt = Math.max(now + DICE_MS, previous);
  const move = {
    playerId: event.player_id,
    track,
    start,
    path,
    startAt,
    arrival: startAt + path.length * STEP_MS,
    queued: previous > now,
  };
  moves.set(event.seq, move);
  arrivals.set(event.player_id, move.arrival);
  return move;
}

export function moveFor(seq: number): Move | undefined {
  return moves.get(seq);
}

/** Сколько мс осталось, пока фишка игрока дойдёт до клетки (0 — уже стоит). */
export function msUntilArrival(playerId: number, now = Date.now()): number {
  return Math.max(0, (arrivals.get(playerId) ?? 0) - now);
}

export function resetMoves() {
  moves.clear();
  arrivals.clear();
}
