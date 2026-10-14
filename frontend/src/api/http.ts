import type { JoinedPlayer, LobbyGame, SessionUser } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "X-CSRFToken": csrfToken() };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(errorText(data, response.status), response.status);
  }
  return data as T;
}

function errorText(data: unknown, status: number): string {
  if (data && typeof data === "object") {
    const detail = (data as Record<string, unknown>).detail;
    if (typeof detail === "string") return detail;
    const first = Object.values(data)[0];
    if (Array.isArray(first) && typeof first[0] === "string") return first[0];
  }
  return status >= 500 ? "Ошибка сервера, попробуйте ещё раз." : "Что-то пошло не так.";
}

export const api = {
  session: () => request<{ user: SessionUser | null }>("GET", "/auth/session/"),
  login: (username: string, password: string) =>
    request<{ user: SessionUser }>("POST", "/auth/login/", { username, password }),
  logout: () => request<{ user: null }>("POST", "/auth/logout/"),

  games: () => request<LobbyGame[]>("GET", "/games/"),
  createGame: (maxPlayers: number) =>
    request<LobbyGame>("POST", "/games/", { max_players: maxPlayers }),
  game: (code: string) => request<LobbyGame>("GET", `/games/${code}/`),
  join: (code: string, name: string) =>
    request<JoinedPlayer>("POST", `/games/${code}/join/`, { name }),
  kick: (code: string, playerId: number) =>
    request<LobbyGame>("DELETE", `/games/${code}/players/${playerId}/`),
  start: (code: string) => request<LobbyGame>("POST", `/games/${code}/start/`),
};
