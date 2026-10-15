/** Кредиты берутся суммами, кратными этому шагу (как BANK_LOAN_STEP на сервере). */
export const LOAN_STEP = 10_000;

/** Сумма в рублях: «25 000 ₽». Игровая валюта — всегда рубль. */
export function money(n: number): string {
  const sign = n < 0 ? "−" : "";
  return `${sign}${Math.abs(n).toLocaleString("ru-RU")}\u00a0₽`;
}

/** Чёрный или белый текст поверх цвета — что лучше читается. */
export function textOn(hex: string): string {
  const n = parseInt(hex.replace("#", ""), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  return 0.299 * r + 0.587 * g + 0.114 * b > 160 ? "#1f2328" : "#ffffff";
}
