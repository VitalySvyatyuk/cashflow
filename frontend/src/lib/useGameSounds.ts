import { useEffect } from "react";

import type { Role } from "../api/types";
import { onGameEvent, useGame } from "../store/game";
import { moveFor, msUntilArrival } from "./movement";
import { preloadSounds, play, type SoundName } from "./sound";
import { STEP_MS } from "./timing";

const MONEY_IN = new Set(["payday", "sold", "loan_taken"]);
const MONEY_OUT = new Set(["paid", "bought", "charity", "downsized", "loan_repaid"]);

/** Звуки игры. Всё, что связано с ходом фишки, звучит, когда фишка дошла. */
export function useGameSounds(role: Role | null, playerId: number | null) {
  useEffect(() => {
    preloadSounds(["dice-1", "dice-2", "dice-3", "step", "income", "expense", "card"]);
  }, []);

  useEffect(() => {
    if (!role) return;
    return onGameEvent((event) => {
      const mine = event.player_id != null && event.player_id === playerId;
      const afterMove = event.player_id != null ? msUntilArrival(event.player_id) : 0;

      switch (event.kind) {
        case "dice_rolled": {
          const count = Math.min(Math.max((event.payload.values as number[]).length, 1), 3);
          play(`dice-${count}` as SoundName);
          return;
        }
        case "moved": {
          const move = moveFor(event.seq);
          move?.path.forEach((_, i) =>
            play("step", { volume: 0.25, delay: move.startAt - Date.now() + i * STEP_MS }),
          );
          return;
        }
        case "card_drawn":
          return play("card", { delay: afterMove });
        case "turn_started":
          if (mine) play("your-turn", { delay: afterMove });
          return;
        case "action_requested":
          if (role === "host") play("request");
          return;
        case "action_approved":
          if (mine) play("approved");
          return;
        case "action_rejected":
          if (mine) play("rejected");
          return;
        case "paused":
          return play("pause");
        case "resumed":
          return play("resume");
        case "game_won":
          return play("win", { delay: afterMove });
      }
      if (MONEY_IN.has(event.kind)) play("income", { delay: afterMove });
      else if (MONEY_OUT.has(event.kind)) play("expense", { delay: afterMove });
    });
  }, [role, playerId]);

  // Ошибка от сервера («Сейчас не ваш ход») — короткий сигнал.
  const error = useGame((s) => s.error);
  useEffect(() => {
    if (error) play("error", { volume: 0.4 });
  }, [error]);
}
