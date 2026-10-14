import { useEffect } from "react";

import { useGame } from "../store/game";

/** Ошибки с сервера («Сейчас не ваш ход») — всплывают и исчезают сами. */
export function Toast() {
  const error = useGame((s) => s.error);
  const clear = useGame((s) => s.clearError);

  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(clear, 4000);
    return () => window.clearTimeout(timer);
  }, [error, clear]);

  if (!error) return null;
  return (
    <div className="toast" role="alert" onClick={clear}>
      {error}
    </div>
  );
}
