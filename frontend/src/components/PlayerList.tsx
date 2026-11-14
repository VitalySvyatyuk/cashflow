import { useBoard } from "../api/board";
import type { GameState, PlayerState } from "../api/types";
import { FAST_TRACK_WIN_INCOME, money } from "../lib/format";
import { useGame } from "../store/game";
import { ProfessionIcon } from "./ProfessionIcon";

export function PlayerList({
  state,
  meId,
  onSelect,
}: {
  state: GameState;
  meId?: number | null;
  onSelect?: (playerId: number) => void;
}) {
  const presence = useGame((s) => s.presence);
  const online = (id: number) => presence?.players.includes(id) ?? false;
  const board = useBoard();
  const dream = (id: number | null) => board?.fast_track.find((c) => c.id === id);
  return (
    <ul className="players">
      {state.players.map((p) => (
        <li
          key={p.id}
          className={`${p.id === state.current_player_id ? "current" : ""} ${onSelect ? "clickable" : ""}`}
          onClick={onSelect ? () => onSelect(p.id) : undefined}
          title={onSelect ? "Финансовый отчёт" : undefined}
        >
          <span className="chip" style={{ background: p.color }} />
          <span
            className={`presence ${online(p.id) ? "on" : "off"}`}
            title={online(p.id) ? "в сети" : "не в сети"}
          />
          <span className="name">
            <ProfessionIcon profession={p.profession} size={18} /> {p.name}
            {p.id === meId && " (вы)"}
            {dream(p.dream_id) && (
              <span className="dream-mark" style={{ color: p.color }} title={`Мечта: ${dream(p.dream_id)!.title}`}>
                {"\u00a0"}★
              </span>
            )}
          </span>
          {state.status !== "lobby" && <span className="cash">{money(p.cash)}</span>}
          {p.id === state.current_player_id && <span className="turn">ход</span>}
          {p.id === state.offer_player_id && <span className="turn offer">решает</span>}
          {(p.skip_turns > 0 || (p.id === state.current_player_id && state.phase === "skip")) && (
            <span className="turn offer" title="Увольнение: пропускает ходы, кубик не бросает">
              уволен(а)
            </span>
          )}
          {state.status !== "lobby" && <GoalBar player={p} />}
        </li>
      ))}
      {presence && meId != null && (
        <li className="muted small">
          <span className={`presence ${presence.host ? "on" : "off"}`} />
          Ведущий {presence.host ? "в сети" : "не в сети"}
        </li>
      )}
    </ul>
  );
}

/** Сколько осталось до цели: в малом круге — чтобы пассивный доход превысил расходы,
 *  в большом — до победы по доходу от бизнесов. Видят все игроки. */
function GoalBar({ player }: { player: PlayerState }) {
  const s = player.statement;
  const rat = player.track === "rat_race";
  const [have, goal] = rat ? [s.passive_income, s.total_expenses] : [s.total_income, FAST_TRACK_WIN_INCOME];
  // Пассивный доход должен именно превысить расходы, доход большого круга — 500 000 ₽.
  const left = rat ? goal - have + 1 : goal - have;
  const done = rat ? s.can_exit_rat_race : have > goal;
  const share = goal > 0 ? Math.min(1, Math.max(0, have / goal)) : done ? 1 : 0;
  return (
    <div
      className="goal"
      title={rat ? "Пассивный доход должен превысить расходы" : `Победа — доход бизнесов больше ${money(goal)} в месяц`}
    >
      <div className="bar">
        <div className={rat ? "" : "fast"} style={{ width: `${share * 100}%` }} />
      </div>
      <span className="small muted">
        {done
          ? rat
            ? "можно в большой круг"
            : "цель достигнута"
          : `${rat ? "до большого круга" : "до победы"}: ${money(Math.max(left, 0))}`}
      </span>
    </div>
  );
}
