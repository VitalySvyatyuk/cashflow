import type { GameState } from "../api/types";
import { money } from "../lib/format";

export function PlayerList({
  state,
  meId,
  onSelect,
}: {
  state: GameState;
  meId?: number | null;
  onSelect?: (playerId: number) => void;
}) {
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
          <span className="name">
            {p.name}
            {p.id === meId && " (вы)"}
          </span>
          {state.status !== "lobby" && <span className="cash">{money(p.cash)}</span>}
          {p.id === state.current_player_id && <span className="turn">ход</span>}
        </li>
      ))}
    </ul>
  );
}
