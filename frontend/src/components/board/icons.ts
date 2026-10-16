/**
 * Значки клеток (шрифт Material Symbols, см. @font-face «Board Icons»). Зелёным
 * «Возможностям» и бизнесу значок не нужен — таких клеток слишком много.
 * Новому значку нужно добавить имя и в файл шрифта public/fonts/material-symbols-board.woff2.
 */
export const CELL_ICONS: Record<string, string> = {
  paycheck: "currency_ruble",
  cashflow_day: "currency_ruble",
  charity: "volunteer_activism",
  market: "tv",
  doodad: "storefront",
  baby: "child_friendly",
  downsized: "work_off",
  dream: "star",
  loss: "trending_down",
};

/** Значок на клетке: тёмный на светлых (жёлтых) клетках, белый на остальных. */
export function iconInk(hex: string): string {
  const n = parseInt(hex.replace("#", ""), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  return 0.299 * r + 0.587 * g + 0.114 * b > 165 ? "rgb(30 25 10 / 0.78)" : "rgb(255 255 255 / 0.93)";
}

/** Цвет светлее (k > 0) или темнее (k < 0) — для объёма фишек. */
export function shade(hex: string, k: number): string {
  const n = parseInt(hex.replace("#", ""), 16);
  return (
    "#" +
    [n >> 16, (n >> 8) & 255, n & 255]
      .map((v) => Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k))
      .map((v) => v.toString(16).padStart(2, "0"))
      .join("")
  );
}
