// Цветовая тема — у каждого своя, хранится в браузере. Цвета — в styles.css ([data-theme]).

export interface Theme {
  id: string;
  label: string;
  /** Цвета кружка в переключателе: поле и акцент. */
  swatch: [string, string];
}

export const THEMES: Theme[] = [
  { id: "felt", label: "Сукно", swatch: ["#1f5e46", "#e8c25e"] },
  { id: "navy", label: "Ночной синий", swatch: ["#1c3a6e", "#ffd36b"] },
  { id: "wine", label: "Бордо", swatch: ["#6b1f2e", "#e9b949"] },
  { id: "brown", label: "Коричневая", swatch: ["#6b4a2e", "#e9b949"] },
  { id: "graphite", label: "Графит", swatch: ["#2a2e34", "#43a047"] },
  { id: "grey", label: "Серая", swatch: ["#c4c9cf", "#3d4a5c"] },
  { id: "paper", label: "Светлая", swatch: ["#f4ead6", "#2e7d32"] },
];

const KEY = "cashflow.theme";
const DEFAULT = THEMES[0].id;

export function loadTheme(): string {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && THEMES.some((t) => t.id === saved)) return saved;
  } catch {
    // недоступно — тема по умолчанию
  }
  return DEFAULT;
}

export function applyTheme(id: string) {
  document.documentElement.dataset.theme = id;
  try {
    localStorage.setItem(KEY, id);
  } catch {
    // тема продержится до перезагрузки
  }
}
