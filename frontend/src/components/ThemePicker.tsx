import { useState } from "react";

import { THEMES, applyTheme, loadTheme } from "../lib/theme";

/** Выбор цветовой темы в шапке: кружки рядом со звуком. */
export function ThemePicker() {
  const [current, setCurrent] = useState(loadTheme);
  return (
    <div className="theme-picker" role="radiogroup" aria-label="Цветовая тема">
      {THEMES.map((t) => (
        <button
          key={t.id}
          role="radio"
          aria-checked={t.id === current}
          title={t.label}
          aria-label={t.label}
          className={`theme-swatch ${t.id === current ? "active" : ""}`}
          style={{ background: `linear-gradient(135deg, ${t.swatch[0]} 55%, ${t.swatch[1]} 55%)` }}
          onClick={() => {
            applyTheme(t.id);
            setCurrent(t.id);
          }}
        />
      ))}
    </div>
  );
}
