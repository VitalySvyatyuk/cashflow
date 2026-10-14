import { useEffect, useRef, useState } from "react";

import { GROUPS, play, useSound } from "../lib/sound";

/** Кнопка звука в шапке: клик — панель с общей громкостью и громкостью по группам. */
export function SoundToggle() {
  const settings = useSound();
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!panel.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const icon = settings.muted || settings.master === 0 ? "🔇" : settings.master < 0.4 ? "🔈" : "🔊";

  return (
    <div className="sound" ref={panel}>
      <button className="icon-button" onClick={() => setOpen((o) => !o)} title="Звук">
        {icon}
      </button>
      {open && (
        <div className="sound-panel">
          <label className="row spread">
            <b>Звук</b>
            <input type="checkbox" checked={!settings.muted} onChange={settings.toggle} />
          </label>
          <Slider label="Общая громкость" value={settings.master} onChange={settings.setMaster} />
          <hr />
          {GROUPS.map((g) => (
            <Slider
              key={g.id}
              label={g.label}
              value={settings.groups[g.id]}
              onChange={(v) => settings.setGroup(g.id, v)}
              onRelease={() => play(g.sample)}
              disabled={settings.muted}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Slider(props: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  onRelease?: () => void;
  disabled?: boolean;
}) {
  return (
    <label className="slider">
      <span>{props.label}</span>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={props.value}
        disabled={props.disabled}
        onChange={(e) => props.onChange(Number(e.target.value))}
        onPointerUp={props.onRelease}
        onKeyUp={props.onRelease}
      />
      <span className="muted small">{Math.round(props.value * 100)}%</span>
    </label>
  );
}
