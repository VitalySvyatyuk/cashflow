import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { api } from "../api/http";
import type { LobbyGame, SessionUser } from "../api/types";
import { useHostSession } from "./useHostSession";

const STATUS = { lobby: "сбор игроков", running: "идёт", paused: "на паузе", finished: "завершена" };

export function HostHomePage() {
  const [user, setUser] = useHostSession();
  if (user === undefined) return <main className="center-page">Загрузка…</main>;
  if (!user?.is_host) return <HostLogin onLogin={setUser} />;
  return <HostDashboard onLogout={() => setUser(null)} />;
}

function HostLogin({ onLogin }: { onLogin: (user: SessionUser) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      const { user } = await api.login(username, password);
      if (!user.is_host) setError("Этот пользователь не ведущий.");
      else onLogin(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти.");
    }
  }

  return (
    <main className="center-page">
      <form className="panel form" onSubmit={submit}>
        <h1>Вход ведущего</h1>
        <label>
          Логин
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Пароль
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Войти</button>
      </form>
    </main>
  );
}

function HostDashboard({ onLogout }: { onLogout: () => void }) {
  const navigate = useNavigate();
  const [games, setGames] = useState<LobbyGame[]>([]);
  const [maxPlayers, setMaxPlayers] = useState(4);
  const [error, setError] = useState("");

  useEffect(() => {
    api.games().then(setGames, () => setError("Не удалось загрузить игры."));
  }, []);

  async function create() {
    try {
      const game = await api.createGame(maxPlayers);
      navigate(`/host/${game.code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать игру.");
    }
  }

  return (
    <main className="center-page">
      <div className="panel wide">
        <div className="row spread">
          <h1>Ведущий</h1>
          <button className="link" onClick={() => api.logout().then(onLogout)}>
            Выйти
          </button>
        </div>
        <div className="row">
          <label>
            Игроков{" "}
            <select value={maxPlayers} onChange={(e) => setMaxPlayers(Number(e.target.value))}>
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
          <button onClick={create}>Создать игру</button>
        </div>
        {error && <p className="error">{error}</p>}
        <h2>Мои игры</h2>
        <ul className="games">
          {games.map((g) => (
            <li key={g.code}>
              <Link to={`/host/${g.code}`}>Игра {g.code}</Link> · {STATUS[g.status]} ·{" "}
              {g.players.length}/{g.max_players} игроков
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
