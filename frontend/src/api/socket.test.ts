import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CLOSE_REMOVED, GameSocket } from "./socket";

/** Подставной WebSocket: тест сам решает, когда соединение открылось или закрылось. */
class FakeWebSocket {
  static OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = 3;
  }
  open() {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.();
  }
  drop(code = 1006) {
    this.readyState = 3;
    this.onclose?.({ code });
  }
}

describe("GameSocket", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
    vi.stubGlobal("window", globalThis);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("переподключается с растущей паузой и сбрасывает её после успеха", () => {
    const statuses: string[] = [];
    new GameSocket("ws://x", { onMessage: () => {}, onStatus: (s) => statuses.push(s) });
    FakeWebSocket.instances[0].open();

    FakeWebSocket.instances[0].drop();
    vi.advanceTimersByTime(499);
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(2); // через 0,5 с

    FakeWebSocket.instances[1].drop();
    vi.advanceTimersByTime(999);
    expect(FakeWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeWebSocket.instances).toHaveLength(3); // через 1 с

    FakeWebSocket.instances[2].open();
    expect(statuses.at(-1)).toBe("open");
    FakeWebSocket.instances[2].drop();
    vi.advanceTimersByTime(500);
    expect(FakeWebSocket.instances).toHaveLength(4); // снова с 0,5 с
  });

  it("пауза не больше 10 секунд", () => {
    new GameSocket("ws://x", { onMessage: () => {}, onStatus: () => {} });
    for (let i = 0; i < 8; i++) {
      FakeWebSocket.instances.at(-1)!.drop();
      vi.advanceTimersByTime(10_000);
    }
    expect(FakeWebSocket.instances).toHaveLength(9);
  });

  it("не переподключается, если игрока убрали", () => {
    const statuses: [string, number | undefined][] = [];
    new GameSocket("ws://x", { onMessage: () => {}, onStatus: (s, c) => statuses.push([s, c]) });
    FakeWebSocket.instances[0].open();
    FakeWebSocket.instances[0].drop(CLOSE_REMOVED);
    vi.advanceTimersByTime(60_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(statuses.at(-1)).toEqual(["closed", CLOSE_REMOVED]);
  });

  it("шлёт ping, пока соединение открыто", () => {
    new GameSocket("ws://x", { onMessage: () => {}, onStatus: () => {} });
    const ws = FakeWebSocket.instances[0];
    ws.open();
    vi.advanceTimersByTime(25_000);
    expect(ws.sent).toEqual(['{"type":"ping"}']);
  });
});
