import { useEffect, useRef, useState } from "react";

import type { GameEvent, PlayerState } from "../api/types";

/** Журнал. Если переданы игроки — можно отфильтровать события одного из них. */
export function EventLog({ events, players }: { events: GameEvent[]; players?: PlayerState[] }) {
  const end = useRef<HTMLDivElement>(null);
  const [only, setOnly] = useState<number | null>(null);
  const shown = events.filter((e) => e.payload.text && (only == null || e.player_id === only));
  useEffect(() => {
    // Тело в скобках: в новых браузерах scrollIntoView возвращает Promise,
    // а React принимает из эффекта только функцию очистки.
    end.current?.scrollIntoView({ block: "end" });
  }, [shown.length]);

  return (
    <>
      {players && (
        <select
          className="log-filter"
          value={only ?? ""}
          onChange={(e) => setOnly(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Все события</option>
          {players.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      )}
      <div className="log">
        {shown.map((e) => (
          <div key={e.seq} className="log-line">
            {e.payload.text}
          </div>
        ))}
        <div ref={end} />
      </div>
    </>
  );
}
