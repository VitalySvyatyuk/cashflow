import { useState } from "react";

import type { GameState, PlayerState } from "../api/types";
import { useGame } from "../store/game";

/** Кнопки по фазе хода. Подробная работа с карточками — на шаге 10. */
export function PlayerActions({ state, me }: { state: GameState; me: PlayerState }) {
  const action = useGame((s) => s.action);
  const cancel = useGame((s) => s.cancel);
  const [quantity, setQuantity] = useState(1);

  const myTurn = state.current_player_id === me.id;
  const disabled = state.status !== "running";
  const myRequests = state.pending_actions.filter((a) => a.player_id === me.id);
  const card = state.current_card;
  const isStock = card?.effect.type === "stock";
  const baseDice = me.track === "rat_race" ? 1 : 2;

  const button = (label: string, kind: string, params?: Record<string, unknown>) => (
    <button key={label} disabled={disabled} onClick={() => action(kind, params)}>
      {label}
    </button>
  );

  const buttons = [];
  if (myTurn) {
    switch (state.phase) {
      case "roll":
        if (me.charity_turns > 0) {
          buttons.push(button(`🎲 ${baseDice} кубик`, "roll", { dice: baseDice }));
          buttons.push(button(`🎲 ${baseDice + 1} кубика`, "roll", { dice: baseDice + 1 }));
        } else {
          buttons.push(button("🎲 Бросить", "roll"));
        }
        break;
      case "choose_deal":
        buttons.push(button("Малая сделка", "choose_deal", { size: "small" }));
        buttons.push(button("Крупная сделка", "choose_deal", { size: "big" }));
        buttons.push(button("Пропустить", "pass"));
        break;
      case "card":
        if (card && (card.category === "small_deal" || card.category === "big_deal")) {
          if (isStock) {
            buttons.push(
              <input
                key="qty"
                type="number"
                min={1}
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
                className="qty"
              />,
            );
          }
          buttons.push(button("Купить", "buy", isStock ? { quantity } : {}));
        }
        buttons.push(button(card?.category === "market" ? "Закрыть карточку" : "Отказаться", "pass"));
        break;
      case "charity":
        buttons.push(button("Пожертвовать", "charity"));
        buttons.push(button("Отказаться", "pass"));
        break;
      case "business":
        buttons.push(button("Купить бизнес", "buy_business"));
        buttons.push(button("Отказаться", "pass"));
        break;
      case "dream":
        buttons.push(button("Купить мечту", "buy_dream"));
        buttons.push(button("Отказаться", "pass"));
        break;
      case "end_turn":
        if (me.track === "rat_race" && me.statement.can_exit_rat_race) {
          buttons.push(button("Выйти на скоростную дорожку", "go_fast_track"));
        }
        buttons.push(button("Завершить ход", "end_turn"));
        break;
    }
  }

  return (
    <div className="actions">
      {buttons.length ? buttons : <span className="muted">Ход другого игрока</span>}
      {myRequests.map((r) => (
        <span key={r.id} className="request">
          ⏳ {r.description}
          <button className="link" onClick={() => cancel(r.id)}>
            отозвать
          </button>
        </span>
      ))}
    </div>
  );
}
