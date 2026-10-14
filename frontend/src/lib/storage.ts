// Токен игрока хранится в браузере, чтобы после перезагрузки вернуться в игру.
// localStorage может быть недоступен (приватный режим) — тогда просто не запоминаем.

interface SavedPlayer {
  token: string;
  name: string;
}

const key = (code: string) => `cashflow.player.${code}`;

export function loadPlayer(code: string): SavedPlayer | null {
  try {
    const raw = localStorage.getItem(key(code));
    return raw ? (JSON.parse(raw) as SavedPlayer) : null;
  } catch {
    return null;
  }
}

export function savePlayer(code: string, player: SavedPlayer) {
  try {
    localStorage.setItem(key(code), JSON.stringify(player));
  } catch {
    // ничего страшного
  }
}

export function forgetPlayer(code: string) {
  try {
    localStorage.removeItem(key(code));
  } catch {
    // ничего страшного
  }
}
