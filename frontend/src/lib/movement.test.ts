import { beforeEach, describe, expect, it } from "vitest";

import type { GameEvent } from "../api/types";
import { msUntilArrival, recordMove, resetMoves } from "./movement";
import { DICE_MS, STEP_MS } from "./timing";

const moved = (seq: number, path: number[], player = 1): GameEvent => ({
  seq,
  player_id: player,
  kind: "moved",
  payload: { track: "rat_race", start: path[0] - 1, path },
  created_at: "",
});

describe("расписание движения фишек", () => {
  beforeEach(resetMoves);

  it("фишка ждёт кубики, потом идёт по шагу на клетку", () => {
    const move = recordMove(moved(1, [1, 2, 3]), 0)!;
    expect(move.startAt).toBe(DICE_MS);
    expect(move.arrival).toBe(DICE_MS + 3 * STEP_MS);
    expect(msUntilArrival(1, 0)).toBe(DICE_MS + 3 * STEP_MS);
    expect(msUntilArrival(1, 10_000)).toBe(0);
  });

  it("следующий ход начинается после окончания предыдущего", () => {
    const first = recordMove(moved(1, [1, 2, 3, 4, 5, 6]), 0)!;
    const second = recordMove(moved(2, [7]), 100)!;
    expect(second.startAt).toBe(first.arrival);
    expect(second.queued).toBe(true);
    expect(first.queued).toBe(false);
  });

  it("у разных игроков расписания независимы", () => {
    recordMove(moved(1, [1, 2, 3, 4, 5, 6], 1), 0);
    const other = recordMove(moved(2, [1], 2), 0)!;
    expect(other.startAt).toBe(DICE_MS);
  });

  it("другие события игнорируются", () => {
    expect(recordMove({ ...moved(1, [1]), kind: "payday" })).toBeNull();
  });
});
