import { create } from "zustand";

export type SoundName =
  | "dice-1"
  | "dice-2"
  | "dice-3"
  | "step"
  | "income"
  | "expense"
  | "card"
  | "your-turn"
  | "request"
  | "approved"
  | "rejected"
  | "error"
  | "pause"
  | "resume"
  | "win";

const MUTED_KEY = "cashflow.muted";

function loadMuted(): boolean {
  try {
    return localStorage.getItem(MUTED_KEY) === "1";
  } catch {
    return false;
  }
}

export const useSound = create<{ muted: boolean; toggle: () => void }>((set, get) => ({
  muted: loadMuted(),
  toggle() {
    const muted = !get().muted;
    try {
      localStorage.setItem(MUTED_KEY, muted ? "1" : "0");
    } catch {
      // не запомним — не страшно
    }
    set({ muted });
  },
}));

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
    if (useSound.getState().muted) return;
    const audio = source(name).cloneNode() as HTMLAudioElement;
    audio.volume = volume;
    // Браузер не даёт играть звук до первого клика на странице — это нормально.
    audio.play().catch(() => undefined);
  };
  if (delay > 0) window.setTimeout(run, delay);
  else run();
}
