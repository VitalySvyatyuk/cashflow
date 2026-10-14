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
const rolls = new Map<number, number>(); // игрок → когда начнёт идти после броска

/**
 * Бросок приходит раньше события moved, но в сообщении уже итоговое состояние.
 * Резервируем время хода сразу: шагов ровно столько, сколько выпало на кубиках.
 */
function recordRoll(event: GameEvent, now: number) {
  const values = (event.payload.values as number[] | undefined) ?? [];
  const steps = values.reduce((a, b) => a + b, 0);
  const startAt = Math.max(now + DICE_MS, arrivals.get(event.player_id!) ?? 0);
  rolls.set(event.player_id!, startAt);
  arrivals.set(event.player_id!, startAt + steps * STEP_MS);
}

/**
 * Расписание хода по событию moved. Фишка ждёт, пока упадут кубики,
 * и не начинает новый ход, пока не закончила предыдущий.
 */
export function recordMove(event: GameEvent, now = Date.now()): Move | null {
  if (event.player_id == null) return null;
  if (event.kind === "dice_rolled") {
    recordRoll(event, now);
    return null;
  }
  if (event.kind !== "moved") return null;
  const { track, start, path } = event.payload as unknown as {
    track: Track;
    start: number;
    path: number[];
  };
  const reserved = rolls.get(event.player_id);
  rolls.delete(event.player_id);
  const startAt = reserved ?? Math.max(now + DICE_MS, arrivals.get(event.player_id) ?? 0);
  const move = {
    playerId: event.player_id,
    track,
    start,
    path,
    startAt,
    arrival: startAt + path.length * STEP_MS,
    // Старт позже обычного броска — значит, ждём окончания предыдущего хода.
    queued: startAt > now + DICE_MS + 100,
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
  rolls.clear();
}
