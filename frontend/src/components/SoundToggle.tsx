import { useSound } from "../lib/sound";

export function SoundToggle() {
  const muted = useSound((s) => s.muted);
  const toggle = useSound((s) => s.toggle);
  return (
    <button className="icon-button" onClick={toggle} title={muted ? "Включить звук" : "Выключить звук"}>
      {muted ? "🔇" : "🔊"}
    </button>
  );
}
