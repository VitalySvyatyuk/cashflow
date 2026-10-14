import { useEffect } from "react";
import { Link, Navigate, useParams } from "react-router";

import { CLOSE_FORBIDDEN, CLOSE_GAME_NOT_FOUND, CLOSE_REMOVED } from "../api/socket";
import { Board } from "../components/board/Board";
import { CardView } from "../components/CardView";
import { Dice } from "../components/dice/Dice";
import { SoundToggle } from "../components/SoundToggle";
import { useGameSounds } from "../lib/useGameSounds";
import { ConnectionBadge } from "../components/ConnectionBadge";
import { EventLog } from "../components/EventLog";
import { FinanceCard } from "../components/FinanceCard";
import { PauseOverlay } from "../components/PauseOverlay";
import { PlayerActions } from "../components/PlayerActions";
import { PlayerList } from "../components/PlayerList";
import { Toast } from "../components/Toast";
import { forgetPlayer, loadPlayer } from "../lib/storage";
import { useCurrentPlayer, useGame, useMe } from "../store/game";

const CLOSE_MESSAGES: Record<number, string> = {
  [CLOSE_FORBIDDEN]: "Вход больше недействителен — войдите заново.",
  [CLOSE_GAME_NOT_FOUND]: "Игра не найдена.",
  [CLOSE_REMOVED]: "Ведущий убрал вас из игры.",
};

export function PlayerPage() {
  const { code = "" } = useParams();
  const saved = loadPlayer(code);
  const connect = useGame((s) => s.connect);
  const disconnect = useGame((s) => s.disconnect);
  const state = useGame((s) => s.state);
  const closeCode = useGame((s) => s.closeCode);
  const me = useMe();
  const current = useCurrentPlayer();
  const role = useGame((s) => s.role);
  const playerId = useGame((s) => s.playerId);
  useGameSounds(role, playerId);

  useEffect(() => {
    if (!saved) return;
    connect(code, saved.token);
    return disconnect;
  }, [code, saved?.token]);

  useEffect(() => {
    if (closeCode === CLOSE_FORBIDDEN || closeCode === CLOSE_REMOVED) forgetPlayer(code);
  }, [closeCode, code]);

  if (!saved) return <Navigate to={`/?code=${code}`} replace />;
  if (closeCode) {
    return (
      <main className="center-page">
        <div className="panel">
          <p>{CLOSE_MESSAGES[closeCode] ?? "Соединение закрыто."}</p>
          <Link to={`/?code=${code}`}>Ко входу</Link>
        </div>
      </main>
    );
  }
  if (!state || !me) return <main className="center-page">Подключение…</main>;

  if (state.status === "lobby") {
    return (
      <main className="center-page">
        <div className="panel">
          <h1>Игра {state.code}</h1>
          <p>Ждём, пока ведущий начнёт игру.</p>
          <PlayerList state={state} meId={me.id} />
          <ConnectionBadge />
        </div>
      </main>
    );
  }

  const paused = state.status === "paused";
  return (
    <div className={`game-layout ${paused ? "is-paused" : ""}`}>
      <header>
        <b>Игра {state.code}</b>
        <span>
          Ход {state.turn_number}: {current?.name}
        </span>
        <span className="row">
          <SoundToggle />
          <ConnectionBadge />
        </span>
      </header>
      <aside className="left">
        <FinanceCard player={me} />
      </aside>
      <main className="board-area">
        <Board state={state} meId={me.id}>
          <Dice values={state.dice} />
          {state.current_card && <CardView card={state.current_card} />}
        </Board>
        {state.status === "finished" && (
          <div className="winner">
            🏆 Победитель: {state.players.find((p) => p.id === state.winner_id)?.name}
          </div>
        )}
      </main>
      <aside className="right">
        <PlayerList state={state} meId={me.id} />
        <EventLog events={state.events} />
      </aside>
      <footer>
        <PlayerActions state={state} me={me} />
      </footer>
      {paused && <PauseOverlay />}
      <Toast />
    </div>
  );
}
