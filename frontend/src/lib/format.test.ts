import { describe, expect, it } from "vitest";

import { money, textOn } from "./format";

describe("format", () => {
  it("деньги с разделителями и знаком минус", () => {
    expect(money(2600).replace(/\s/g, " ")).toBe("$2 600");
    expect(money(-500)).toBe("−$500");
  });

  it("на жёлтом — тёмный текст, на синем — белый", () => {
    expect(textOn("#fdd835")).toBe("#1f2328");
    expect(textOn("#1e88e5")).toBe("#ffffff");
  });
});
