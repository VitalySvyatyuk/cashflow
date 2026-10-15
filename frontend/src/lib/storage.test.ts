import { afterEach, describe, expect, it, vi } from "vitest";

import { forgetPlayer, loadPlayer, savePlayer } from "./storage";

describe("хранение токена игрока", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("работает, даже если localStorage запрещён", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => {
        throw new DOMException("denied", "SecurityError");
      },
      setItem: () => {
        throw new DOMException("denied", "SecurityError");
      },
      removeItem: () => {
        throw new DOMException("denied", "SecurityError");
      },
    });
    savePlayer("1234", { token: "t", name: "Маша" });
    expect(loadPlayer("1234")).toEqual({ token: "t", name: "Маша" });
    forgetPlayer("1234");
    expect(loadPlayer("1234")).toBeNull();
  });
});
