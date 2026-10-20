import { useState } from "react";

import type { GameState } from "../api/types";

/**
 * Конец игры. Победа — большая табличка поверх всего (закрывается, чтобы посмотреть поле),
 * под ней остаётся плашка с победителем. Ведущий завершил игру — только плашка.
 */
export function GameOverBanner({ state, meId = null }: { state: GameState; meId?: number | null }) {
  const [closed, setClosed] = useState(false);
  if (state.status !== "finished") return null;
  const winner = state.players.find((p) => p.id === state.winner_id);
  if (!winner) return <div className="winner">Ведущий завершил игру</div>;

  const how = [...state.events].reverse().find((e) => e.kind === "game_won")?.payload.text;
  return (
    <>
      <div className="winner">🏆 Победитель: {winner.name}</div>
      {!closed && (
        <div className="victory" role="dialog" aria-label="Победа">
          <div className="victory-box" style={{ borderColor: winner.color }}>
            <div className="victory-cup">🏆</div>
            <h1 className="victory-title">
              {winner.id === meId ? "Поздравляю, вы выиграли!" : `Победа: ${winner.name}!`}
            </h1>
            {how && <p className="victory-how">{how}</p>}
            <button onClick={() => setClosed(true)}>Посмотреть поле</button>
          </div>
        </div>
      )}
    </>
  );
}

/** Игру закрыли ещё в лобби — профессии никому не раздали, показывать поле незачем. */
export function closedInLobby(state: GameState): boolean {
  return state.status === "finished" && state.players.every((p) => !p.profession);
}
