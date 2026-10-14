import { useState } from "react";

import type { PlayerState } from "../../api/types";
import { money } from "../../lib/format";
import { Modal } from "../Modal";
import { FinanceSheet, assetLabel } from "./FinanceSheet";

/** Левая панель игрока: главное о деньгах и путь к выходу из крысиных бегов. */
export function FinanceSummary({ player }: { player: PlayerState }) {
  const [open, setOpen] = useState(false);
  const s = player.statement;
  const progress = s.total_expenses ? Math.min(1, s.passive_income / s.total_expenses) : 0;

  return (
    <div className="finance">
      <h2>{player.profession?.name ?? "Без профессии"}</h2>
      <div className="cash">
        <span className="muted">Наличные</span>
        <b>{money(player.cash)}</b>
      </div>
      <dl>
        <dt>Общий доход</dt>
        <dd>{money(s.total_income)}</dd>
        <dt>Расходы</dt>
        <dd>{money(s.total_expenses)}</dd>
        <dt>Денежный поток</dt>
        <dd className={s.cashflow < 0 ? "negative strong" : "strong"}>{money(s.cashflow)}</dd>
      </dl>

      {player.track === "rat_race" ? (
        <div className="exit-progress" title="Пассивный доход должен превысить расходы">
          <div className="muted small">
            Выход из крысиных бегов: {money(s.passive_income)} из {money(s.total_expenses)}
          </div>
          <div className="bar">
            <div style={{ width: `${progress * 100}%` }} />
          </div>
        </div>
      ) : (
        <div className="muted small">
          Скоростная дорожка: {money(player.fast_track_income)} в День денежного потока
        </div>
      )}

      <h3>Активы</h3>
      {player.assets.length ? (
        <ul className="plain">
          {player.assets.map((a) => (
            <li key={a.id}>
              {assetLabel(a)} <span className="muted">{a.cashflow ? `+${money(a.cashflow)}` : ""}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted small">Пока нет</p>
      )}

      <button className="secondary" onClick={() => setOpen(true)}>
        Финансовый отчёт и кредиты
      </button>
      {open && (
        <Modal title={`${player.name} — ${player.profession?.name ?? ""}`} onClose={() => setOpen(false)}>
          <FinanceSheet player={player} readOnly={false} />
        </Modal>
      )}
    </div>
  );
}
