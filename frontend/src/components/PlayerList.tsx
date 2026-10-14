import type { GameState } from "../api/types";
import { money } from "../lib/format";
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
          </span>
          {state.status !== "lobby" && <span className="cash">{money(p.cash)}</span>}
          {p.id === state.current_player_id && <span className="turn">ход</span>}
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
