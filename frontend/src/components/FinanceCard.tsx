import type { PlayerState } from "../api/types";
import { money } from "../lib/format";

/** Карточка игрока: финансовый отчёт. Подробная версия — на шаге 10. */
export function FinanceCard({ player }: { player: PlayerState }) {
  const s = player.statement;
  return (
    <div className="finance">
      <h2>{player.profession?.name ?? "Без профессии"}</h2>
      <dl>
        <dt>Наличные</dt>
        <dd className="strong">{money(player.cash)}</dd>
        <dt>Зарплата</dt>
        <dd>{money(s.salary)}</dd>
        <dt>Пассивный доход</dt>
        <dd>{money(s.passive_income)}</dd>
        <dt>Расходы</dt>
        <dd>{money(s.total_expenses)}</dd>
        <dt>Денежный поток</dt>
        <dd className="strong">{money(s.cashflow)}</dd>
        {player.children > 0 && (
          <>
            <dt>Дети</dt>
            <dd>{player.children}</dd>
          </>
        )}
      </dl>
      <details>
        <summary>Активы ({player.assets.length})</summary>
        <ul>
          {player.assets.map((a) => (
            <li key={a.id}>
              {a.title}
              {a.kind === "stock" ? ` × ${a.quantity}` : ""} · {money(a.cashflow)}/мес
            </li>
          ))}
        </ul>
      </details>
      <details>
        <summary>Пассивы ({player.liabilities.length})</summary>
        <ul>
          {player.liabilities.map((l) => (
            <li key={l.id}>
              {l.title}: {money(l.balance)}
              {l.payment ? ` · ${money(l.payment)}/мес` : ""}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
