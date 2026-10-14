import type { GameState } from "../api/types";
import { useGame } from "../store/game";

export function ApprovalQueue({ state }: { state: GameState }) {
  const decide = useGame((s) => s.decide);
  const name = (id: number) => state.players.find((p) => p.id === id)?.name ?? "?";

  if (!state.pending_actions.length) return <p className="muted">Заявок нет</p>;
  return (
    <ul className="approvals">
      {state.pending_actions.map((a) => (
        <li key={a.id}>
          <div>
            <b>{name(a.player_id)}</b>: {a.description}
          </div>
          <div className="row">
            <button className="ok" onClick={() => decide(a.id, true)}>
              ✓ Одобрить
            </button>
            <button
              className="danger"
              onClick={() => decide(a.id, false, {}, window.prompt("Комментарий (необязательно)") ?? "")}
            >
              ✕ Отклонить
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function HostControls({ state }: { state: GameState }) {
  const action = useGame((s) => s.action);
  const paused = state.status === "paused";

  const adjust = () => {
    const who = window.prompt(
      `Кому? Введите номер:\n${state.players.map((p, i) => `${i + 1}. ${p.name}`).join("\n")}`,
    );
    const player = state.players[Number(who) - 1];
    if (!player) return;
    const amount = Number(window.prompt(`Сумма для ${player.name} (минус — списать)`));
    if (!amount) return;
    const reason = window.prompt("Причина (необязательно)") ?? "";
    action("adjust_cash", { player_id: player.id, amount, reason });
  };

  return (
    <div className="host-controls">
      <button className={paused ? "ok" : "warn"} onClick={() => action(paused ? "resume" : "pause")}>
        {paused ? "▶ Разморозить" : "❄ Заморозить"}
      </button>
      <button onClick={() => action("undo")}>↶ Отменить</button>
      <button onClick={() => action("next_turn")}>⏭ Передать ход</button>
      <button onClick={adjust}>$ Деньги</button>
    </div>
  );
}
