import type { ServerMessage } from "./types";

// Коды закрытия с сервера (game/consumers.py): после них переподключаться бессмысленно.
export const CLOSE_FORBIDDEN = 4403;
export const CLOSE_GAME_NOT_FOUND = 4404;
export const CLOSE_REMOVED = 4410;
const FINAL_CODES = [CLOSE_FORBIDDEN, CLOSE_GAME_NOT_FOUND, CLOSE_REMOVED];

const PING_INTERVAL = 25_000;
const MAX_RETRY_DELAY = 10_000;

export type ConnectionStatus = "connecting" | "open" | "reconnecting" | "closed";

interface Handlers {
  onMessage: (message: ServerMessage) => void;
  onStatus: (status: ConnectionStatus, closeCode?: number) => void;
}

/** WebSocket игры с автоматическим переподключением. */
export class GameSocket {
  private ws: WebSocket | null = null;
  private retries = 0;
  private stopped = false;
  private pingTimer: number | undefined;
  private retryTimer: number | undefined;

  constructor(
    private readonly url: string,
    private readonly handlers: Handlers,
  ) {
    this.open();
  }

  static url(code: string, token?: string) {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const query = token ? `?token=${encodeURIComponent(token)}` : "";
    return `${scheme}://${location.host}/ws/games/${encodeURIComponent(code)}/${query}`;
  }

  send(message: object) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  close() {
    this.stopped = true;
    window.clearInterval(this.pingTimer);
    window.clearTimeout(this.retryTimer);
    this.ws?.close();
  }

  private open() {
    this.handlers.onStatus(this.retries ? "reconnecting" : "connecting");
    const ws = new WebSocket(this.url);
    this.ws = ws;

    ws.onopen = () => {
      this.retries = 0;
      this.handlers.onStatus("open");
      this.pingTimer = window.setInterval(() => this.send({ type: "ping" }), PING_INTERVAL);
    };
    ws.onmessage = (e) => this.handlers.onMessage(JSON.parse(e.data) as ServerMessage);
    ws.onclose = (e) => {
      window.clearInterval(this.pingTimer);
      if (this.stopped) return;
      if (FINAL_CODES.includes(e.code)) {
        this.stopped = true;
        this.handlers.onStatus("closed", e.code);
        return;
      }
      const delay = Math.min(500 * 2 ** this.retries, MAX_RETRY_DELAY);
      this.retries += 1;
      this.handlers.onStatus("reconnecting");
      this.retryTimer = window.setTimeout(() => this.open(), delay);
    };
  }
}
