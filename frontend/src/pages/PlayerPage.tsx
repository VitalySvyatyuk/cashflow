import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router";

import { CLOSE_FORBIDDEN, CLOSE_GAME_NOT_FOUND, CLOSE_REMOVED } from "../api/socket";
import { Board } from "../components/board/Board";
import { GameCard } from "../components/card/GameCard";
import { Dice } from "../components/dice/Dice";
import { SoundToggle } from "../components/SoundToggle";
import { useGameSounds } from "../lib/useGameSounds";
import { ConnectionBadge } from "../components/ConnectionBadge";
import { EventLog } from "../components/EventLog";
import { FinanceSheet } from "../components/finance/FinanceSheet";
import { GameOverBanner, closedInLobby } from "../components/GameOver";
import { FinanceSummary } from "../components/finance/FinanceSummary";
import { Modal } from "../components/Modal";
import { PauseOverlay } from "../components/PauseOverlay";
import { PlayerActions } from "../components/PlayerActions";
import { PlayerList } from "../components/PlayerList";
import { ProfessionIcon } from "../components/ProfessionIcon";
import { Toast } from "../components/Toast";
import { forgetPlayer, isWelcomed, loadPlayer, markWelcomed } from "../lib/storage";
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
  const settled = useGame((s) => s.view);
  const closeCode = useGame((s) => s.closeCode);
  const me = useMe();
  const current = useCurrentPlayer();
  const [viewing, setViewing] = useState<number | null>(null);
  const [welcomeClosed, setWelcomeClosed] = useState(false);
  const viewingPlayer = useGame((s) => s.view?.players.find((p) => p.id === viewing) ?? null);
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

  if (closedInLobby(state)) {
    return (
      <main className="center-page">
        <div className="panel">
          <h1>Игра {state.code}</h1>
          <p>Ведущий завершил игру.</p>
          <Link to="/">Ко входу</Link>
        </div>
      </main>
    );
  }

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

  const view = settled ?? state;
  const paused = state.status === "paused";
  const showWelcome =
    !welcomeClosed && state.status !== "finished" && !!me.profession && !isWelcomed(saved.token);
  const closeWelcome = () => {
    markWelcomed(saved.token);
    setWelcomeClosed(true);
  };
  return (
    <div className={`game-layout ${paused ? "is-paused" : ""}`}>
      <header>
        <b>Игра {state.code}</b>
        <span>
          Ход {view.turn_number}: {current?.name}
        </span>
        <span className="row">
          <SoundToggle />
          <ConnectionBadge />
        </span>
      </header>
      <aside className="left">
        <FinanceSummary player={me} />
      </aside>
      <main className="board-area">
        <Board state={state} meId={me.id}>
          {view.current_card ? (
            <GameCard key={view.current_card.id} state={view} me={me} />
          ) : (
            <Dice values={state.dice} />
          )}
        </Board>
        <GameOverBanner state={view} />
      </main>
      <aside className="right">
        <PlayerList state={view} meId={me.id} onSelect={setViewing} />
        <EventLog events={view.events} />
      </aside>
      <footer>
        <PlayerActions state={view} me={me} busy={settled !== state} />
      </footer>
      {viewingPlayer && (
        <Modal
          title={`${viewingPlayer.name} — ${viewingPlayer.profession?.name ?? ""}`}
          onClose={() => setViewing(null)}
        >
          <FinanceSheet player={viewingPlayer} readOnly={viewingPlayer.id !== me.id} />
        </Modal>
      )}
      {showWelcome && me.profession && (
        <Modal title="Добро пожаловать в игру!" onClose={closeWelcome}>
          <div className="welcome">
            <ProfessionIcon profession={me.profession} size={64} />
            <p>
              Сегодня ваша профессия: <b>{me.profession.name}</b>
            </p>
            <button onClick={closeWelcome}>Начать</button>
          </div>
        </Modal>
      )}
      {paused && <PauseOverlay />}
      <Toast />
    </div>
  );
}
