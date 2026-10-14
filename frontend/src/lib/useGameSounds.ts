import { useEffect } from "react";

import type { Role } from "../api/types";
import { onGameEvent, useGame } from "../store/game";
import { moveFor, msUntilArrival } from "./movement";
import { preloadSounds, play, type SoundName } from "./sound";
import { STEP_MS } from "./timing";

// Всё, что связано с деньгами, звенит монетами: поступление и списание — по-разному.
const MONEY_IN = new Set(["payday", "sold", "loan_taken", "auto_loan"]);
const MONEY_OUT = new Set(["paid", "bought", "charity", "downsized", "loan_repaid"]);

/** Звуки игры. Всё, что связано с ходом фишки, звучит, когда фишка дошла. */
export function useGameSounds(role: Role | null, playerId: number | null) {
  useEffect(() => {
    preloadSounds(["dice-1", "dice-2", "dice-3", "step", "coins-in", "coins-out", "page-flip"]);
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
          // Карточка открывается, когда фишка дошла, — как перелистнуть страницу журнала.
          return play("page-flip", { volume: 0.7, delay: afterMove });
        case "cash_adjusted":
          return play((event.payload.amount as number) > 0 ? "coins-in" : "coins-out");
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
      if (MONEY_IN.has(event.kind)) play("coins-in", { delay: afterMove });
      else if (MONEY_OUT.has(event.kind)) play("coins-out", { delay: afterMove });
    });
  }, [role, playerId]);

  // Ошибка от сервера («Сейчас не ваш ход») — короткий сигнал.
  const error = useGame((s) => s.error);
  useEffect(() => {
    if (error) play("error", { volume: 0.4 });
  }, [error]);
}
