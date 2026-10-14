import { useEffect, useState } from "react";

import { api } from "../api/http";
import type { SessionUser } from "../api/types";

/** undefined — ещё загружаем, null — не вошёл. Заодно получает cookie csrftoken. */
export function useHostSession() {
  const [user, setUser] = useState<SessionUser | null | undefined>(undefined);
  useEffect(() => {
    api
      .session()
      .then((r) => setUser(r.user))
      .catch(() => setUser(null));
  }, []);
  return [user, setUser] as const;
}
