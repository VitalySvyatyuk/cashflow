import { useState } from "react";

import type { GameState, PlayerState } from "../api/types";
import { money } from "../lib/format";
import { useGame } from "../store/game";

/** Кнопки по фазе хода. Подробная работа с карточками — на шаге 10. */
export function PlayerActions({
  state,
  me,
  busy = false,
  asHost = false,
}: {
  state: GameState;
  me: PlayerState;
  /** Фишка ещё идёт — ждём, пока экран догонит сервер. */
  busy?: boolean;
  /** Ведущий действует за игрока: без заявок, сразу. */
  asHost?: boolean;
}) {
  const send = useGame((s) => s.action);
  const action = (kind: string, params: Record<string, unknown> = {}) =>
    send(kind, asHost ? { ...params, player_id: me.id } : params);
  const cancel = useGame((s) => s.cancel);
  const [quantity, setQuantity] = useState(1);
  const [dice, setDice] = useState<number | null>(null);

  const myTurn = state.current_player_id === me.id;
  const disabled = state.status !== "running" || busy;
  const myRequests = state.pending_actions.filter((a) => a.player_id === me.id);
  const card = state.current_card;
  const isStock = card?.effect.type === "stock";
  // Без выбора — как в правилах: 1 кубик на крысиных бегах, 2 на скоростной дорожке.
  const diceCount = dice ?? (me.track === "rat_race" ? 1 : 2);

  const button = (label: string, kind: string, params?: Record<string, unknown>) => (
    <button key={label} disabled={disabled} onClick={() => action(kind, params)}>
      {label}
    </button>
  );

  const buttons = [];
  if (myTurn) {
    switch (state.phase) {
      case "roll":
        buttons.push(
          <div key="dice-count" className="segmented" role="group" aria-label="Сколько кубиков">
            {[1, 2, 3].map((n) => (
              <button
                key={n}
                className={n === diceCount ? "active" : ""}
                aria-pressed={n === diceCount}
                onClick={() => setDice(n)}
              >
                {n}
              </button>
            ))}
          </div>,
        );
        buttons.push(button(`🎲 Бросить ${diceCount === 1 ? "кубик" : `${diceCount} кубика`}`, "roll", { dice: diceCount }));
        break;
      case "choose_deal":
        buttons.push(button("Малая сделка", "choose_deal", { size: "small" }));
        buttons.push(button("Крупная сделка", "choose_deal", { size: "big" }));
        buttons.push(button("Пропустить", "pass"));
        break;
      case "card":
        if (card && (card.category === "small_deal" || card.category === "big_deal")) {
          const effect = card.effect as { price?: number; down_payment?: number };
          const price = isStock ? (effect.price ?? 0) * quantity : (effect.down_payment ?? 0);
          if (isStock) {
            buttons.push(
              <label key="qty" className="row">
                Акций
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
                  className="qty"
                />
              </label>,
            );
          }
          buttons.push(
            <button
              key="buy"
              disabled={disabled || price > me.cash}
              title={price > me.cash ? "Не хватает наличных — можно взять кредит в финансовом отчёте" : undefined}
              onClick={() => action("buy", isStock ? { quantity } : {})}
            >
              Купить за {money(price)}
            </button>,
          );
        }
        buttons.push(button(card?.category === "market" ? "Закрыть карточку" : "Отказаться", "pass"));
        break;
      case "pay": {
        const amount = (card?.effect as { amount?: number } | undefined)?.amount ?? 0;
        buttons.push(
          <button
            key="pay"
            disabled={disabled}
            title={amount > me.cash ? "Наличных не хватает — недостающее возьмётся в кредит" : undefined}
            onClick={() => action("pay_card")}
          >
            Заплатить {money(amount)}
          </button>,
        );
        break;
      }
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
        buttons.push(button("Завершить ход", "end_turn"));
        break;
    }
  }

  return (
    <div className="actions">
      {buttons.length ? buttons : <span className="muted">Ход другого игрока</span>}
      {!asHost &&
        myRequests.map((r) => (
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
