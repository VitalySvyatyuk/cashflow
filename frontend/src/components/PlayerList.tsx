import type { GameState } from "../api/types";
import { money } from "../lib/format";

export function PlayerList({ state, meId }: { state: GameState; meId?: number | null }) {
  return (
    <ul className="players">
      {state.players.map((p) => (
        <li key={p.id} className={p.id === state.current_player_id ? "current" : ""}>
          <span className="chip" style={{ background: p.color }} />
          <span className="name">
            {p.name}
            {p.id === meId && " (вы)"}
          </span>
          <span className="cash">{money(p.cash)}</span>
          {p.id === state.current_player_id && <span className="turn">ход</span>}
        </li>
      ))}
    </ul>
  );
}
