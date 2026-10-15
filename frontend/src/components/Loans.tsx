import { useState } from "react";

import type { GameState, PlayerState } from "../api/types";
import { LOAN_STEP, money } from "../lib/format";
import { useGame } from "../store/game";
import { MoneyInput } from "./MoneyInput";

/** Платёж в месяц по займу между игроками — как loan_payment на сервере. */
export const loanPayment = (amount: number, rate: number) => Math.floor((amount * rate) / 100);

const terms = (amount: number, rate: number) =>
  `${money(amount)} под ${rate}% в месяц (платёж ${money(loanPayment(amount, rate))})`;

/** «Взять кредит» в момент сделки: заявка ведущему, он решает — дать или нет. */
export function LoanRequest({
  need,
  disabled,
  asHost,
  onRequest,
}: {
  /** Сколько не хватает на покупку (0 — хватает). */
  need: number;
  disabled: boolean;
  asHost: boolean;
  onRequest: (amount: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const initial = Math.max(LOAN_STEP, Math.ceil(need / LOAN_STEP) * LOAN_STEP);
  if (!open) {
    return (
      <button disabled={disabled} onClick={() => setOpen(true)}>
        Взять кредит
      </button>
    );
  }
  return (
    <span className="row">
      <span className="muted small">Кредит банка, 10% в месяц:</span>
      <MoneyInput
        key={initial}
        label={asHost ? "Выдать" : "Попросить у ведущего"}
        initial={initial}
        onSubmit={(amount) => {
          onRequest(amount);
          setOpen(false);
        }}
      />
      <button className="link" onClick={() => setOpen(false)}>
        отмена
      </button>
    </span>
  );
}

/** Предложения займов: входящие — принять или отказаться, свои — отозвать. */
export function LoanOffers({ state, me }: { state: GameState; me: PlayerState }) {
  const action = useGame((s) => s.action);
  const name = (id: number) => state.players.find((p) => p.id === id)?.name ?? "";
  const paused = state.status !== "running";
  return (
    <>
      {state.loan_offers
        .filter((o) => o.borrower_id === me.id)
        .map((o) => (
          <span key={o.id} className="loan-offer">
            💰 {name(o.lender_id)} предлагает в долг {terms(o.amount, o.rate)}
            <button className="ok" disabled={paused} onClick={() => action("accept_loan", { offer_id: o.id })}>
              Принять
            </button>
            <button disabled={paused} onClick={() => action("decline_loan", { offer_id: o.id })}>
              Отказаться
            </button>
          </span>
        ))}
      {state.loan_offers
        .filter((o) => o.lender_id === me.id)
        .map((o) => (
          <span key={o.id} className="request">
            ⏳ Ждём ответа {name(o.borrower_id)}: заём {terms(o.amount, o.rate)}
            <button className="link" onClick={() => action("decline_loan", { offer_id: o.id })}>
              отозвать
            </button>
          </span>
        ))}
    </>
  );
}

/** Дать в долг другому игроку под выбранный процент (можно 0). */
export function LendForm({ lender, borrower }: { lender: PlayerState; borrower: PlayerState }) {
  const action = useGame((s) => s.action);
  const [amount, setAmount] = useState(Math.min(LOAN_STEP, Math.max(lender.cash, 0)));
  const [rate, setRate] = useState(0);
  const valid = amount > 0 && amount <= lender.cash && rate >= 0 && rate <= 100;
  return (
    <div className="lend">
      <h3>Дать в долг игроку {borrower.name}</h3>
      <div className="row">
        <label className="row">
          Сумма
          <input
            type="number"
            min={1}
            max={lender.cash}
            step={1000}
            value={amount}
            onChange={(e) => setAmount(Math.max(0, Math.floor(Number(e.target.value))))}
          />
          ₽
        </label>
        <label className="row">
          Процент в месяц
          <input
            type="number"
            min={0}
            max={100}
            value={rate}
            className="qty"
            onChange={(e) => setRate(Math.min(100, Math.max(0, Math.floor(Number(e.target.value)))))}
          />
          %
        </label>
      </div>
      <p className="muted small">
        {borrower.name} будет платить вам {money(loanPayment(amount, rate))} в месяц — это ваш пассивный
        доход. Деньги уйдут, когда {borrower.name} согласится. У вас {money(lender.cash)}.
      </p>
      <button disabled={!valid} onClick={() => action("offer_loan", { borrower_id: borrower.id, amount, rate })}>
        Предложить заём
      </button>
    </div>
  );
}
