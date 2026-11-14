import { useState } from "react";

import type { PlayerState } from "../../api/types";
import { FAST_TRACK_WIN_INCOME, money, signed } from "../../lib/format";
import { useGame } from "../../store/game";
import { LendForm } from "../Loans";
import { Modal } from "../Modal";
import { ProfessionIcon } from "../ProfessionIcon";
import { FinanceSheet, assetLabel } from "./FinanceSheet";

/** Цена консультации ведущего (как CONSULTATION_PRICE на сервере). */
const CONSULTATION_PRICE = 1_000;

/** Левая панель игрока: главное о деньгах и путь к выходу в большой круг. */
export function FinanceSummary({ player }: { player: PlayerState }) {
  const [open, setOpen] = useState(false);
  const [lending, setLending] = useState(false);
  const view = useGame((s) => s.view);
  const action = useGame((s) => s.action);
  const others = view?.players.filter((p) => p.id !== player.id) ?? [];
  const canLend = view?.status === "running" && others.length > 0;
  const s = player.statement;
  const progress = s.total_expenses ? Math.min(1, s.passive_income / s.total_expenses) : 0;

  return (
    <div className="finance">
      <h2 className="row">
        <ProfessionIcon profession={player.profession} size={28} />
        {player.profession?.name ?? "Без профессии"}
      </h2>
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
            Выход в большой круг: пассивный доход {money(s.passive_income)} из{" "}
            {money(s.total_expenses)}
          </div>
          <div className="bar">
            <div style={{ width: `${progress * 100}%` }} />
          </div>
          {s.can_exit_rat_race && (
            <p className="exit-ready">
              Условие выполнено! Скажите ведущему: «Я хочу выйти в большой круг».
            </p>
          )}
        </div>
      ) : (
        <div className="exit-progress" title="Общий доход растёт с покупкой бизнесов">
          <div className="muted small">
            Победа: общий доход {money(s.total_income)} из {money(FAST_TRACK_WIN_INCOME)}
          </div>
          <div className="bar">
            <div style={{ width: `${Math.min(1, s.total_income / FAST_TRACK_WIN_INCOME) * 100}%` }} />
          </div>
        </div>
      )}

      <h3>Активы</h3>
      {player.assets.length ? (
        <ul className="plain">
          {player.assets.map((a) => (
            <li key={a.id}>
              {assetLabel(a)} <span className="muted">{a.cashflow ? signed(a.cashflow) : ""}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted small">Пока нет</p>
      )}

      <button className="secondary" onClick={() => setOpen(true)}>
        Финансовый отчёт и кредиты
      </button>
      {canLend && (
        <button className="secondary" onClick={() => setLending(true)}>
          🤝 Дать в долг игроку
        </button>
      )}
      {view?.status === "running" && (
        <button
          className="secondary"
          disabled={player.cash < CONSULTATION_PRICE}
          title={player.cash < CONSULTATION_PRICE ? "Не хватает наличных" : "Списывается с ваших наличных"}
          onClick={() => action("consultation")}
        >
          💬 Получить консультацию ({money(CONSULTATION_PRICE)})
        </button>
      )}
      {open && (
        <Modal title={`${player.name} — ${player.profession?.name ?? ""}`} onClose={() => setOpen(false)}>
          <FinanceSheet player={player} readOnly={false} />
          {canLend && <LendForm lender={player} borrowers={others} />}
        </Modal>
      )}
      {lending && (
        <Modal title="Заём другому игроку" onClose={() => setLending(false)}>
          <LendForm lender={player} borrowers={others} />
        </Modal>
      )}
    </div>
  );
}
