import { create } from "zustand";

export type SoundName =
  | "dice-1"
  | "dice-2"
  | "dice-3"
  | "step"
  | "coins-in"
  | "coins-out"
  | "page-flip"
  | "your-turn"
  | "request"
  | "approved"
  | "rejected"
  | "error"
  | "pause"
  | "resume"
  | "win";

export type SoundGroup = "dice" | "steps" | "money" | "cards" | "signals";

export const GROUPS: { id: SoundGroup; label: string; sample: SoundName }[] = [
  { id: "dice", label: "Кубики", sample: "dice-2" },
  { id: "steps", label: "Шаги фишки", sample: "step" },
  { id: "money", label: "Деньги", sample: "coins-in" },
  { id: "cards", label: "Карточки", sample: "page-flip" },
  { id: "signals", label: "Сигналы", sample: "your-turn" },
];

const GROUP_OF: Record<SoundName, SoundGroup> = {
  "dice-1": "dice",
  "dice-2": "dice",
  "dice-3": "dice",
  step: "steps",
  "coins-in": "money",
  "coins-out": "money",
  "page-flip": "cards",
  "your-turn": "signals",
  request: "signals",
  approved: "signals",
  rejected: "signals",
  error: "signals",
  pause: "signals",
  resume: "signals",
  win: "signals",
};

interface SoundSettings {
  muted: boolean;
  /** Общая громкость, 0…1 */
  master: number;
  groups: Record<SoundGroup, number>;
}

const DEFAULTS: SoundSettings = {
  muted: false,
  master: 0.8,
  groups: { dice: 1, steps: 1, money: 1, cards: 1, signals: 1 },
};
const KEY = "cashflow.sound";

function load(): SoundSettings {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) ?? "{}") as Partial<SoundSettings>;
    return { ...DEFAULTS, ...saved, groups: { ...DEFAULTS.groups, ...saved.groups } };
  } catch {
    return DEFAULTS;
  }
}

interface SoundStore extends SoundSettings {
  toggle: () => void;
  setMaster: (value: number) => void;
  setGroup: (group: SoundGroup, value: number) => void;
}

export const useSound = create<SoundStore>((set, get) => {
  const save = (patch: Partial<SoundSettings>) => {
    set(patch);
    const { muted, master, groups } = get();
    try {
      localStorage.setItem(KEY, JSON.stringify({ muted, master, groups }));
    } catch {
      // не запомним — не страшно
    }
  };
  return {
    ...load(),
    toggle: () => save({ muted: !get().muted }),
    setMaster: (master) => save({ master, muted: false }),
    setGroup: (group, value) => save({ groups: { ...get().groups, [group]: value } }),
  };
});

/** Итоговая громкость звука: базовая × группа × общая. */
export function effectiveVolume(name: SoundName, base: number, settings: SoundSettings): number {
  if (settings.muted) return 0;
  return Math.min(1, base * settings.master * settings.groups[GROUP_OF[name]]);
}

const cache = new Map<SoundName, HTMLAudioElement>();

function source(name: SoundName) {
  let audio = cache.get(name);
  if (!audio) {
    audio = new Audio(`/sounds/${name}.mp3`);
    audio.preload = "auto";
    cache.set(name, audio);
  }
  return audio;
}

/** Загрузить звуки заранее, чтобы первый бросок не был беззвучным. */
export function preloadSounds(names: SoundName[]) {
  names.forEach(source);
}

/** Проиграть звук; копия элемента — чтобы одинаковые звуки могли накладываться. */
export function play(name: SoundName, { volume = 0.6, delay = 0 } = {}) {
  const run = () => {
    const level = effectiveVolume(name, volume, useSound.getState());
    if (level <= 0) return;
    const audio = source(name).cloneNode() as HTMLAudioElement;
    audio.volume = level;
    // Браузер не даёт играть звук до первого клика на странице — это нормально.
    audio.play().catch(() => undefined);
  };
  if (delay > 0) window.setTimeout(run, delay);
  else run();
}
