import { useEffect, useRef } from "react";

import type { GameEvent } from "../api/types";

export function EventLog({ events }: { events: GameEvent[] }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // Тело в скобках: в новых браузерах scrollIntoView возвращает Promise,
    // а React принимает из эффекта только функцию очистки.
    end.current?.scrollIntoView({ block: "end" });
  }, [events.length]);

  return (
    <div className="log">
      {events
        .filter((e) => e.payload.text)
        .map((e) => (
          <div key={e.seq} className="log-line">
            {e.payload.text}
          </div>
        ))}
      <div ref={end} />
    </div>
  );
}
