import type { Asset, PlayerState } from "../../api/types";
import { money } from "../../lib/format";
import { useGame } from "../../store/game";
import { MoneyInput } from "../MoneyInput";

const BANK_LOAN = "Банковский кредит";

/** Финансовый отчёт как на карточке настольной игры. */
export function FinanceSheet({ player, readOnly }: { player: PlayerState; readOnly: boolean }) {
  const action = useGame((s) => s.action);
  const s = player.statement;
  const prof = player.profession;
  const incomeAssets = player.assets.filter((a) => a.cashflow !== 0);

  return (
    <div className="sheet">
      <div className="sheet-grid">
        <section>
          <h3>Доходы</h3>
          <Row label="Зарплата" value={s.salary} />
          {incomeAssets.map((a) => (
            <Row key={a.id} label={assetLabel(a)} value={a.cashflow} muted />
          ))}
          <Row label="Пассивный доход" value={s.passive_income} strong />
          <Row label="Общий доход" value={s.total_income} strong />
        </section>

        <section>
          <h3>Расходы</h3>
          {prof && <Row label="Налоги" value={prof.taxes} />}
          {prof && <Row label="Прочие расходы" value={prof.other_expenses} />}
          {prof && player.children > 0 && (
            <Row
              label={`Дети: ${player.children} × ${money(prof.per_child_expense)}`}
              value={player.children * prof.per_child_expense}
            />
          )}
          {player.liabilities
            .filter((l) => l.payment > 0)
            .map((l) => (
              <Row key={l.id} label={l.title} value={l.payment} />
            ))}
          <Row label="Общие расходы" value={s.total_expenses} strong />
        </section>
      </div>

      <div className={`sheet-cashflow ${s.cashflow < 0 ? "negative" : ""}`}>
        <span>Денежный поток в месяц</span>
        <b>{money(s.cashflow)}</b>
      </div>

      <div className="sheet-grid">
        <section>
          <h3>Активы</h3>
          {player.assets.length === 0 && <p className="muted">Пока нет</p>}
          {player.assets.map((a) => (
            <div key={a.id} className="sheet-row">
              <span>{assetLabel(a)}</span>
              <span className="muted">
                {a.kind === "stock" ? `по ${money(a.cost)}` : money(a.cost)}
              </span>
            </div>
          ))}
        </section>

        <section>
          <h3>Пассивы</h3>
          {player.liabilities.map((l) => (
            <div key={l.id} className="sheet-row">
              <span>{l.title}</span>
              <span className="row">
                {money(l.balance)}
                {!readOnly && !l.asset_id && (
                  <RepayControl
                    title={l.title}
                    balance={l.balance}
                    cash={player.cash}
                    onRepay={(amount) => action("repay_loan", { liability_id: l.id, amount })}
                  />
                )}
              </span>
            </div>
          ))}
          {!readOnly && (
            <div className="sheet-row">
              <span>Новый кредит (10% в месяц)</span>
              <MoneyInput label="Взять" onSubmit={(amount) => action("take_loan", { amount })} />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function RepayControl(props: {
  title: string;
  balance: number;
  cash: number;
  onRepay: (amount: number) => void;
}) {
  if (props.title === BANK_LOAN) {
    return <MoneyInput label="Погасить" max={Math.min(props.balance, props.cash)} onSubmit={props.onRepay} />;
  }
  return (
    <button
      className="small-button"
      disabled={props.cash < props.balance}
      title={props.cash < props.balance ? "Не хватает наличных" : undefined}
      onClick={() => props.onRepay(props.balance)}
    >
      Погасить
    </button>
  );
}

function Row({ label, value, strong, muted }: { label: string; value: number; strong?: boolean; muted?: boolean }) {
  return (
    <div className={`sheet-row ${strong ? "strong" : ""} ${muted ? "muted" : ""}`}>
      <span>{label}</span>
      <span>{money(value)}</span>
    </div>
  );
}

export function assetLabel(a: Asset): string {
  return a.kind === "stock" ? `${a.title} × ${a.quantity}` : a.title;
}
