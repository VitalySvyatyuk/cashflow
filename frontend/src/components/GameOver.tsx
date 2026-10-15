import type { GameState } from "../api/types";

/** Плашка поверх поля, когда игра закончилась: победитель или «завершена ведущим». */
export function GameOverBanner({ state }: { state: GameState }) {
  if (state.status !== "finished") return null;
  const winner = state.players.find((p) => p.id === state.winner_id);
  return (
    <div className="winner">{winner ? `🏆 Победитель: ${winner.name}` : "Ведущий завершил игру"}</div>
  );
}

/** Игру закрыли ещё в лобби — профессии никому не раздали, показывать поле незачем. */
export function closedInLobby(state: GameState): boolean {
  return state.status === "finished" && state.players.every((p) => !p.profession);
}
