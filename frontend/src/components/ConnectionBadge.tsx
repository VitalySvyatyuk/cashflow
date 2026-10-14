import { useGame } from "../store/game";

const LABELS = {
  connecting: "подключение…",
  open: "в сети",
  reconnecting: "переподключение…",
  closed: "нет связи",
};

export function ConnectionBadge() {
  const connection = useGame((s) => s.connection);
  return <span className={`badge badge-${connection}`}>{LABELS[connection]}</span>;
}
