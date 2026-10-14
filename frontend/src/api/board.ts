import { useEffect, useState } from "react";

import type { BoardCell, Track } from "./types";

export type Board = Record<Track, BoardCell[]>;

let cached: Promise<Board> | null = null;

function loadBoard(): Promise<Board> {
  cached ??= fetch("/api/board/")
    .then((r) => {
      if (!r.ok) throw new Error(String(r.status));
      return r.json() as Promise<BoardCell[]>;
    })
    .then((cells) => ({
      rat_race: cells.filter((c) => c.track === "rat_race"),
      fast_track: cells.filter((c) => c.track === "fast_track"),
    }))
    .catch((err) => {
      cached = null; // попробуем ещё раз при следующем монтировании
      throw err;
    });
  return cached;
}

/** Клетки поля — не меняются во время игры, грузим один раз. */
export function useBoard(): Board | null {
  const [board, setBoard] = useState<Board | null>(null);
  useEffect(() => {
    let alive = true;
    loadBoard().then((b) => alive && setBoard(b), () => undefined);
    return () => {
      alive = false;
    };
  }, []);
  return board;
}
