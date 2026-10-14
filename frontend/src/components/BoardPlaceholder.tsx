import type { GameState } from "../api/types";

/** Временная заглушка — настоящее поле с кольцами будет на шаге 8. */
export function BoardPlaceholder({ state }: { state: GameState }) {
  return (
    <div className="board-placeholder">
      <div>Здесь будет игровое поле</div>
      <ul>
        {state.players.map((p) => (
          <li key={p.id}>
            <span className="chip" style={{ background: p.color }} /> {p.name}:{" "}
            {p.track === "rat_race" ? "крысиные бега" : "скоростная дорожка"}, клетка {p.position}
          </li>
        ))}
      </ul>
      {state.dice.length > 0 && <div className="dice">🎲 {state.dice.join(" + ")}</div>}
    </div>
  );
}
