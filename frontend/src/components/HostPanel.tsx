import { useState } from "react";

import type { GameState, PendingAction, PlayerState } from "../api/types";
import { money } from "../lib/format";
import { useGame } from "../store/game";
import { Modal } from "./Modal";

// Какие параметры заявки ведущий может поправить перед одобрением.
const EDITABLE: Record<string, string> = {
  quantity: "Количество",
  amount: "Сумма, ₽",
};

export function ApprovalQueue({ state }: { state: GameState }) {
  if (!state.pending_actions.length) return <p className="muted">Заявок нет</p>;
  return (
    <ul className="approvals">
      {state.pending_actions.map((a) => (
        <Approval key={a.id} request={a} state={state} />
      ))}
    </ul>
  );
}

function Approval({ request, state }: { request: PendingAction; state: GameState }) {
  const decide = useGame((s) => s.decide);
  const player = state.players.find((p) => p.id === request.player_id);
  const editable = Object.keys(EDITABLE).filter((k) => typeof request.payload[k] === "number");
  const [params, setParams] = useState<Record<string, number>>(() =>
    Object.fromEntries(editable.map((k) => [k, request.payload[k] as number])),
  );
  const [rejecting, setRejecting] = useState(false);
  const [comment, setComment] = useState("");
  const changed = editable.filter((k) => params[k] !== request.payload[k]);

  return (
    <li>
      <div>
        <span className="chip" style={{ background: player?.color }} /> <b>{player?.name}</b>:{" "}
        {request.description}
      </div>
      {editable.map((key) => (
        <label key={key} className="row small">
          {EDITABLE[key]}
          <input
            type="number"
            min={1}
            value={params[key]}
            onChange={(e) => setParams({ ...params, [key]: Number(e.target.value) })}
            className="qty"
          />
        </label>
      ))}
      {rejecting ? (
        <div className="row">
          <input
            autoFocus
            placeholder="Комментарий (необязательно)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && decide(request.id, false, {}, comment)}
          />
          <button className="danger" onClick={() => decide(request.id, false, {}, comment)}>
            Отклонить
          </button>
          <button className="link" onClick={() => setRejecting(false)}>
            отмена
          </button>
        </div>
      ) : (
        <div className="row">
          <button
            className="ok"
            onClick={() =>
              decide(request.id, true, Object.fromEntries(changed.map((k) => [k, params[k]])))
            }
          >
            ✓ Одобрить{changed.length ? " с правкой" : ""}
          </button>
          <button className="danger" onClick={() => setRejecting(true)}>
            ✕ Отклонить
          </button>
        </div>
      )}
    </li>
  );
}

export function HostControls({ state }: { state: GameState }) {
  const action = useGame((s) => s.action);
  const paused = state.status === "paused";
  const [adjusting, setAdjusting] = useState(false);

  return (
    <div className="host-controls">
      <button
        className={paused ? "ok" : "warn"}
        onClick={() => action(paused ? "resume" : "pause")}
        disabled={state.status === "finished"}
        title={paused ? "Разморозить игру" : "Заморозить игру"}
      >
        {paused ? "▶" : "❄"} <span className="label">{paused ? "Разморозить" : "Заморозить"}</span>
      </button>
      <button onClick={() => action("undo")} title="Отменить последнее действие">
        ↶ <span className="label">Отменить</span>
      </button>
      <button
        onClick={() => action("next_turn")}
        disabled={state.status === "finished"}
        title="Передать ход следующему игроку"
      >
        ⏭ <span className="label">Передать ход</span>
      </button>
      <button onClick={() => setAdjusting(true)} title="Начислить или списать деньги">
        ₽ <span className="label">Деньги</span>
      </button>
      {adjusting && <AdjustCash state={state} onClose={() => setAdjusting(false)} />}
    </div>
  );
}

/** Ведущий переводит игрока в большой круг, когда пассивный доход превысил расходы. */
export function FastTrackButton({ state, player }: { state: GameState; player: PlayerState }) {
  const action = useGame((s) => s.action);
  if (player.track !== "rat_race" || !player.statement.can_exit_rat_race) return null;
  const midTurn =
    player.id === state.current_player_id && !["roll", "end_turn"].includes(state.phase);
  return (
    <button
      className="ok small-button"
      disabled={midTurn || state.status === "finished"}
      title={midTurn ? "Дождитесь конца хода игрока" : "Пассивный доход превысил расходы"}
      onClick={(e) => {
        e.stopPropagation();
        action("go_fast_track", { player_id: player.id });
      }}
    >
      Перевести в большой круг
    </button>
  );
}

function AdjustCash({ state, onClose }: { state: GameState; onClose: () => void }) {
  const action = useGame((s) => s.action);
  const [playerId, setPlayerId] = useState(state.current_player_id ?? state.players[0]?.id);
  const [sign, setSign] = useState<1 | -1>(1);
  const [amount, setAmount] = useState(1000);
  const [reason, setReason] = useState("");

  const submit = () => {
    action("adjust_cash", { player_id: playerId, amount: sign * amount, reason });
    onClose();
  };

  return (
    <Modal title="Корректировка денег" onClose={onClose}>
      <div className="form">
        <label>
          Игрок
          <select value={playerId} onChange={(e) => setPlayerId(Number(e.target.value))}>
            {state.players.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <div className="row">
          <div className="segmented">
            <button className={sign === 1 ? "active" : ""} onClick={() => setSign(1)}>
              + Начислить
            </button>
            <button className={sign === -1 ? "active" : ""} onClick={() => setSign(-1)}>
              − Списать
            </button>
          </div>
          <span className="money-input">
            <input type="number" min={1} value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
            ₽
          </span>
        </div>
        <label>
          Причина (увидят все в журнале)
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Например: штраф" />
        </label>
        <button disabled={!playerId || amount <= 0} onClick={submit}>
          {sign === 1 ? "Начислить" : "Списать"} {money(amount)}
        </button>
      </div>
    </Modal>
  );
}
