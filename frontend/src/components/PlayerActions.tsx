import { useState } from "react";

import { useBoard } from "../api/board";
import type { GameState, PlayerState } from "../api/types";
import { money } from "../lib/format";
import { useGame } from "../store/game";
import { LoanOffers, LoanRequest } from "./Loans";

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
  const board = useBoard();
  // Клетка бизнеса — там, где стоит игрок, чей ход (бизнес могли предложить другому).
  const turnPlayer = state.players.find((p) => p.id === state.current_player_id);
  const turnCell = turnPlayer && board?.[turnPlayer.track].find((c) => c.position === turnPlayer.position);
  const currentCellCost = (turnCell?.effect as { cost?: number } | undefined)?.cost ?? 0;

  // От сделки отказались — решает тот, кому её предложили по кругу.
  const myTurn = (state.offer_player_id ?? state.current_player_id) === me.id;
  const offered = state.offer_player_id === me.id;
  const offerTo = state.players.find((p) => p.id === state.offer_player_id);
  const disabled = state.status !== "running" || busy;
  const myRequests = state.pending_actions.filter((a) => a.player_id === me.id);
  const card = state.current_card;
  const isStock = card?.effect.type === "stock";
  // По правилам: 1 кубик на малом круге, 2 на большом. Выбор — только после благотворительности.
  const defaultDice = me.track === "rat_race" ? 1 : 2;
  const diceCount = dice !== null && me.dice_options.includes(dice) ? dice : defaultDice;

  // Кредит банка в момент сделки: заявка ведущему (ведущий за игрока — сразу).
  const loanButton = (price: number) => (
    <LoanRequest
      key="loan"
      need={price - me.cash}
      disabled={disabled}
      asHost={asHost}
      onRequest={(amount) => action("take_loan", { amount })}
    />
  );

  const button = (label: string, kind: string, params?: Record<string, unknown>) => (
    <button key={label} disabled={disabled} onClick={() => action(kind, params)}>
      {label}
    </button>
  );

  const waitingNames = state.players
    .filter((p) => state.stock_waiting.includes(p.id))
    .map((p) => p.name)
    .join(", ");

  const buttons = [];
  if (state.stock_waiting.includes(me.id)) {
    const symbol = (card?.effect as { symbol?: string } | undefined)?.symbol;
    buttons.push(
      <span key="stock-note" className="offer-note">
        Продайте акции {symbol} на карточке или откажитесь:
      </span>,
    );
    buttons.push(button("Отказаться", "decline_sell"));
  }
  if (offered) {
    const owner = state.players.find((p) => p.id === state.current_player_id);
    buttons.push(
      <span key="offer" className="offer-note">
        {owner?.name} отказался(ась){asHost ? ":" : " — предлагают вам:"}
      </span>,
    );
  }
  if (myTurn) {
    switch (state.phase) {
      case "roll":
        if (me.dice_options.length > 1) {
          buttons.push(
            <div key="dice-count" className="segmented" role="group" aria-label="Сколько кубиков">
              {me.dice_options.map((n) => (
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
          buttons.push(
            <span key="dice-hint" className="muted small">
              {me.track === "rat_race"
                ? `благотворительность: ещё ${me.charity_turns} ${me.charity_turns === 1 ? "ход" : "хода"}`
                : "благотворительность: до конца игры"}
            </span>,
          );
        }
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
              title={price > me.cash ? "Не хватает наличных — возьмите кредит" : undefined}
              onClick={() => action("buy", isStock ? { quantity } : {})}
            >
              Купить за {money(price)}
            </button>,
          );
          buttons.push(loanButton(price));
        }
        buttons.push(button(card?.category === "market" ? "Закрыть карточку" : "Отказаться", "pass"));
        break;
      case "income": {
        const perPayday = me.track === "rat_race" ? me.statement.cashflow : me.fast_track_income;
        const amount = perPayday * state.paydays;
        const times = state.paydays > 1 ? ` (${state.paydays} раза)` : "";
        buttons.push(
          <button key="income" className="ok" disabled={disabled} onClick={() => action("collect_income")}>
            {amount >= 0
              ? `Получить ${money(amount)}${times}`
              : `Оплатить расходы ${money(-amount)}${times}`}
          </button>,
        );
        break;
      }
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
      case "charity": {
        // Малый круг — 10% общего дохода, большой — сумма с клетки (как на сервере).
        const amount =
          me.track === "rat_race" ? Math.floor(me.statement.total_income / 10) : currentCellCost;
        buttons.push(
          <span key="charity-note" className="muted small">
            {me.track === "rat_race"
              ? "10% дохода — и 3 следующих хода можно бросать 1 или 2 кубика"
              : "до конца игры можно бросать 1, 2 или 3 кубика"}
          </span>,
        );
        buttons.push(
          <button
            key="charity"
            className="ok"
            disabled={disabled || amount > me.cash}
            title={amount > me.cash ? "Не хватает наличных — возьмите кредит" : undefined}
            onClick={() => action("charity")}
          >
            Пожертвовать {money(amount)}
          </button>,
        );
        if (amount > me.cash) buttons.push(loanButton(amount));
        buttons.push(button("Отказаться", "pass"));
        break;
      }
      case "business":
        buttons.push(button("Купить бизнес", "buy_business"));
        buttons.push(loanButton(currentCellCost));
        buttons.push(button("Отказаться", "pass"));
        break;
      case "dream":
        buttons.push(button("Купить мечту", "buy_dream"));
        buttons.push(button("Отказаться", "pass"));
        break;
      case "skip":
        buttons.push(
          <span key="skip" className="offer-note">
            Увольнение: этот ход пропускаете — кубик не бросаете
            {me.skip_turns > 0 ? ` (пропустите ещё ${me.skip_turns})` : ", со следующего хода снова играете"}.
            Продавать, брать и давать в долг можно.
          </span>,
        );
        buttons.push(button("Завершить ход", "end_turn"));
        break;
      case "end_turn":
        if (state.stock_waiting.length) {
          buttons.push(
            <span key="waiting" className="muted">
              Ждём решения по акциям: {waitingNames}
            </span>,
          );
        }
        buttons.push(
          <button
            key="end"
            disabled={disabled || state.stock_waiting.length > 0}
            onClick={() => action("end_turn")}
          >
            Завершить ход
          </button>,
        );
        break;
    }
  }

  return (
    <div className="actions">
      {buttons.length ? (
        buttons
      ) : offerTo ? (
        <span className="muted">Сделку решает {offerTo.name}</span>
      ) : (
        <span className="muted">Ход другого игрока</span>
      )}
      {!asHost && <LoanOffers state={state} me={me} />}
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
