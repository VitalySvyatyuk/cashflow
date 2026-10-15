import { create } from "zustand";

import { GameSocket, type ConnectionStatus } from "../api/socket";
import type { GameEvent, GameState, PlayerState, Presence, Role } from "../api/types";
import { msUntilArrival, recordMove, resetMoves } from "../lib/movement";

/** previous — состояние до этого события (например, где фишка стояла до броска). */
type Listener = (event: GameEvent, state: GameState, previous: GameState | null) => void;

interface GameStore {
  connection: ConnectionStatus;
  closeCode: number | null;
  role: Role | null;
  playerId: number | null;
  /** Состояние с сервера — для поля и кубиков, они анимируются сами. */
  state: GameState | null;
  /**
   * Состояние для остального экрана (деньги, журнал, карточка, кнопки):
   * пока фишка идёт, показываем прежнее и обновляем, когда она дошла.
   */
  view: GameState | null;
  /** Кто сейчас на связи. */
  presence: Presence | null;
  error: string | null;

  connect: (code: string, token?: string) => void;
  disconnect: () => void;
  action: (kind: string, params?: Record<string, unknown>) => void;
  decide: (id: number, approve: boolean, params?: Record<string, unknown>, comment?: string) => void;
  cancel: (id: number) => void;
  clearError: () => void;
}

let socket: GameSocket | null = null;
let viewTimer: number | undefined;
const listeners = new Set<Listener>();

/** Подписка на события игры — для анимаций и звуков. Возвращает функцию отписки. */
export function onGameEvent(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export const useGame = create<GameStore>((set, get) => {
  const settle = (state: GameState) => {
    window.clearTimeout(viewTimer);
    const wait = Math.max(0, ...state.players.map((p) => msUntilArrival(p.id)));
    if (wait === 0) set({ view: state });
    else viewTimer = window.setTimeout(() => set({ view: get().state }), wait);
  };

  const send = (message: object) => {
    if (!socket?.send(message)) set({ error: "Нет связи с сервером — подождите." });
  };

  return {
    connection: "closed",
    closeCode: null,
    role: null,
    playerId: null,
    state: null,
    view: null,
    presence: null,
    error: null,

    connect(code, token) {
      get().disconnect();
      resetMoves();
      window.clearTimeout(viewTimer);
      set({
        state: null,
        view: null,
        presence: null,
        role: null,
        playerId: null,
        closeCode: null,
        error: null,
      });
      socket = new GameSocket(GameSocket.url(code, token), {
        onStatus: (connection, closeCode) => set({ connection, closeCode: closeCode ?? null }),
        onMessage: (message) => {
          switch (message.type) {
            case "hello":
              set({
                role: message.role,
                playerId: message.player_id,
                state: message.state,
                view: message.state,
                presence: message.presence,
              });
              break;
            case "presence":
              set({ presence: message });
              break;
            case "state":
              set({ state: message.state });
              settle(message.state);
              break;
            case "event": {
              const previous = get().state;
              recordMove(message.event); // до подписчиков: им нужно расписание хода
              set({ state: message.state });
              settle(message.state);
              // Подписчики вызываются в той же задаче — React отрисует новое состояние
              // вместе с их правками (например, фишка остаётся на старте до анимации).
              listeners.forEach((l) => l(message.event, message.state, previous));
              break;
            }
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

/** Игрок этого экрана (для ведущего — null), в «показанном» состоянии. */
export function useMe(): PlayerState | null {
  return useGame((s) => s.view?.players.find((p) => p.id === s.playerId) ?? null);
}

export function useCurrentPlayer(): PlayerState | null {
  return useGame((s) => s.view?.players.find((p) => p.id === s.view?.current_player_id) ?? null);
}

export function useOnline(playerId: number): boolean {
  return useGame((s) => s.presence?.players.includes(playerId) ?? false);
}
