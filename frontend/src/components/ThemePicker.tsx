import { useEffect, useRef, useState } from "react";

import { THEMES, applyTheme, loadTheme, type Theme } from "../lib/theme";

const swatchStyle = (t: Theme) => ({
  background: `linear-gradient(135deg, ${t.swatch[0]} 55%, ${t.swatch[1]} 55%)`,
});

/** Выбор цветовой темы в шапке: кружок текущей темы, по клику — список тем. */
export function ThemePicker() {
  const [current, setCurrent] = useState(loadTheme);
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);
  const theme = THEMES.find((t) => t.id === current) ?? THEMES[0];

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!panel.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="theme-picker" ref={panel}>
      <button
        className="icon-button"
        title={`Цветовая тема: ${theme.label}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="theme-swatch" style={swatchStyle(theme)} />
      </button>
      {open && (
        <div className="theme-menu" role="menu">
          {THEMES.map((t) => (
            <button
              key={t.id}
              role="menuitemradio"
              aria-checked={t.id === current}
              className={t.id === current ? "active" : ""}
              onClick={() => {
                applyTheme(t.id);
                setCurrent(t.id);
                setOpen(false);
              }}
            >
              <span className="theme-swatch" style={swatchStyle(t)} />
              {t.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
