// Токен игрока хранится в браузере, чтобы после перезагрузки вернуться в игру.
// Если localStorage недоступен (строгие настройки приватности, встроенные браузеры),
// держим токен в памяти: войти и играть можно, только перезагрузка страницы его потеряет.

interface SavedPlayer {
  token: string;
  name: string;
}

const key = (code: string) => `cashflow.player.${code}`;
const memory = new Map<string, SavedPlayer>();

export function loadPlayer(code: string): SavedPlayer | null {
  try {
    const raw = localStorage.getItem(key(code));
    if (raw) return JSON.parse(raw) as SavedPlayer;
  } catch {
    // недоступно — смотрим в памяти
  }
  return memory.get(code) ?? null;
}

export function savePlayer(code: string, player: SavedPlayer) {
  memory.set(code, player);
  try {
    localStorage.setItem(key(code), JSON.stringify(player));
  } catch {
    // останется только в памяти
  }
}

export function forgetPlayer(code: string) {
  memory.delete(code);
  try {
    localStorage.removeItem(key(code));
  } catch {
    // ничего страшного
  }
}
