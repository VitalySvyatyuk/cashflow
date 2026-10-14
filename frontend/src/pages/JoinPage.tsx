import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { api } from "../api/http";
import { loadPlayer, savePlayer } from "../lib/storage";

export function JoinPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [code, setCode] = useState(params.get("code") ?? "");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const saved = code.length === 4 ? loadPlayer(code) : null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const player = await api.join(code, name);
      savePlayer(code, { token: player.token, name: player.name });
      navigate(`/play/${code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="center-page">
      <form className="panel form" onSubmit={submit}>
        <h1>Денежный поток</h1>
        <label>
          Код игры
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 4))}
            inputMode="numeric"
            autoComplete="off"
            placeholder="1234"
            className="code-input"
            autoFocus
          />
        </label>
        {saved && (
          <button type="button" onClick={() => navigate(`/play/${code}`)}>
            Вернуться как {saved.name}
          </button>
        )}
        <label>
          Ваше имя
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={40} />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy || code.length !== 4 || !name.trim()}>
          Войти в игру
        </button>
      </form>
    </main>
  );
}
