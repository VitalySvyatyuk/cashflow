import { create } from "zustand";

import { GameSocket, type ConnectionStatus } from "../api/socket";
import type { GameEvent, GameState, PlayerState, Role } from "../api/types";

type Listener = (event: GameEvent, state: GameState) => void;

interface GameStore {
  connection: ConnectionStatus;
  closeCode: number | null;
  role: Role | null;
  playerId: number | null;
  state: GameState | null;
  error: string | null;

  connect: (code: string, token?: string) => void;
  disconnect: () => void;
  action: (kind: string, params?: Record<string, unknown>) => void;
  decide: (id: number, approve: boolean, params?: Record<string, unknown>, comment?: string) => void;
  cancel: (id: number) => void;
  clearError: () => void;
}

let socket: GameSocket | null = null;
const listeners = new Set<Listener>();

/** Подписка на события игры — для анимаций и звуков. Возвращает функцию отписки. */
export function onGameEvent(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const useGame = create<GameStore>((set, get) => {
  const send = (message: object) => {
    if (!socket?.send(message)) set({ error: "Нет связи с сервером — подождите." });
  };

  return {
    connection: "closed",
    closeCode: null,
    role: null,
    playerId: null,
    state: null,
    error: null,

    connect(code, token) {
      get().disconnect();
      set({ state: null, role: null, playerId: null, closeCode: null, error: null });
      socket = new GameSocket(GameSocket.url(code, token), {
        onStatus: (connection, closeCode) => set({ connection, closeCode: closeCode ?? null }),
        onMessage: (message) => {
          switch (message.type) {
            case "hello":
              set({ role: message.role, playerId: message.player_id, state: message.state });
              break;
            case "state":
              set({ state: message.state });
              break;
            case "event":
              set({ state: message.state });
              listeners.forEach((l) => l(message.event, message.state));
              break;
            case "error":
              set({ error: message.message });
              break;
          }
        },
      });
    },

    disconnect() {
      socket?.close();
      socket = null;
      set({ connection: "closed" });
    },

    action: (kind, params = {}) => send({ type: "action", kind, params }),
    decide: (id, approve, params = {}, comment = "") =>
      send({ type: "decide", id, approve, params, comment }),
    cancel: (id) => send({ type: "cancel", id }),
    clearError: () => set({ error: null }),
  };
});

/** Игрок этого экрана (для ведущего — null). */
export function useMe(): PlayerState | null {
  return useGame((s) => s.state?.players.find((p) => p.id === s.playerId) ?? null);
}

export function useCurrentPlayer(): PlayerState | null {
  return useGame((s) => s.state?.players.find((p) => p.id === s.state?.current_player_id) ?? null);
}
