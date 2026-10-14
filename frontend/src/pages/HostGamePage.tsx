import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router";

import { api } from "../api/http";
import type { GameState } from "../api/types";
import { Board } from "../components/board/Board";
import { GameCard } from "../components/card/GameCard";
import { FinanceSheet } from "../components/finance/FinanceSheet";
import { Modal } from "../components/Modal";
import { Dice } from "../components/dice/Dice";
import { SoundToggle } from "../components/SoundToggle";
import { useGameSounds } from "../lib/useGameSounds";
import { ConnectionBadge } from "../components/ConnectionBadge";
import { EventLog } from "../components/EventLog";
import { ApprovalQueue, HostControls } from "../components/HostPanel";
import { Toast } from "../components/Toast";
import { money } from "../lib/format";
import { useCurrentPlayer, useGame } from "../store/game";
import { useHostSession } from "./useHostSession";

export function HostGamePage() {
  const { code = "" } = useParams();
  const [user] = useHostSession();
  const connect = useGame((s) => s.connect);
  const disconnect = useGame((s) => s.disconnect);
  const state = useGame((s) => s.state);
  const closeCode = useGame((s) => s.closeCode);

  useEffect(() => {
    if (!user?.is_host) return;
    connect(code);
    return disconnect;
  }, [user, code, connect, disconnect]);

  if (user === undefined) return <main className="center-page">Загрузка…</main>;
  if (!user?.is_host) return <Navigate to="/host" replace />;
  if (closeCode) {
    return (
      <main className="center-page">
        <div className="panel">
          Игра не найдена. <Link to="/host">К списку игр</Link>
        </div>
      </main>
    );
  }
  if (!state) return <main className="center-page">Подключение…</main>;
  return state.status === "lobby" ? <HostLobby state={state} /> : <HostGame state={state} />;
}

function HostLobby({ state }: { state: GameState }) {
  const setError = (message: string) => useGame.setState({ error: message });
  const run = (promise: Promise<unknown>) =>
    promise.catch((err) => setError(err instanceof Error ? err.message : "Ошибка"));

  return (
    <main className="center-page">
      <div className="panel wide">
        <Link to="/host">← Мои игры</Link>
        <p>Код для игроков:</p>
        <div className="big-code">{state.code}</div>
        <p className="muted">
          Игроки открывают {location.origin} и вводят код и имя. Подключилось{" "}
          {state.players.length} из {state.max_players}.
        </p>
        <ul className="players">
          {state.players.map((p) => (
            <li key={p.id}>
              <span className="chip" style={{ background: p.color }} />
              <span className="name">{p.name}</span>
              <button className="link" onClick={() => run(api.kick(state.code, p.id))}>
                убрать
              </button>
            </li>
          ))}
        </ul>
        <button disabled={!state.players.length} onClick={() => run(api.start(state.code))}>
          Начать игру
        </button>
        <ConnectionBadge />
      </div>
      <Toast />
    </main>
  );
}

function HostGame({ state }: { state: GameState }) {
  const current = useCurrentPlayer();
  const view = useGame((s) => s.view) ?? state;
  const [viewing, setViewing] = useState<number | null>(null);
  const viewingPlayer = view.players.find((p) => p.id === viewing);
  useGameSounds("host", null);

  return (
    <div className="game-layout host">
      <header>
        <b>Игра {state.code} · ведущий</b>
        <span>
          Ход {view.turn_number}: {current?.name}
          {state.status === "paused" && " · ❄ заморожена"}
        </span>
        <span className="row">
          <SoundToggle />
          <ConnectionBadge />
        </span>
      </header>
      <aside className="left">
        <h2>Игроки</h2>
        <table className="overview">
          <thead>
            <tr>
              <th />
              <th>Наличные</th>
              <th>Поток</th>
              <th>Пассив.</th>
            </tr>
          </thead>
          <tbody>
            {view.players.map((p) => (
              <tr
                key={p.id}
                className={`clickable ${p.id === view.current_player_id ? "current" : ""}`}
                onClick={() => setViewing(p.id)}
                title="Финансовый отчёт"
              >
                <td>
                  <span className="chip" style={{ background: p.color }} /> {p.name}
                  <div className="muted small">{p.profession?.name}</div>
                </td>
                <td>{money(p.cash)}</td>
                <td className={p.statement.cashflow < 0 ? "negative" : ""}>{money(p.statement.cashflow)}</td>
                <td>{money(p.statement.passive_income)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </aside>
      <main className="board-area">
        <Board state={state} meId={null}>
          {view.current_card ? (
            <GameCard key={view.current_card.id} state={view} me={null} />
          ) : (
            <Dice values={state.dice} />
          )}
        </Board>
        {view.status === "finished" && (
          <div className="winner">
            🏆 Победитель: {view.players.find((p) => p.id === view.winner_id)?.name}
          </div>
        )}
      </main>
      <aside className="right">
        <h2>Заявки</h2>
        <ApprovalQueue state={state} />
        <h2>Журнал</h2>
        <EventLog events={view.events} />
      </aside>
      <footer>
        <HostControls state={state} />
      </footer>
      {viewingPlayer && (
        <Modal
          title={`${viewingPlayer.name} — ${viewingPlayer.profession?.name ?? ""}`}
          onClose={() => setViewing(null)}
        >
          <FinanceSheet player={viewingPlayer} readOnly />
        </Modal>
      )}
      <Toast />
    </div>
  );
}
