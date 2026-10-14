import type { Profession } from "../api/types";

/** Иконка профессии: картинка из админки или эмодзи. */
export function ProfessionIcon({ profession, size = 22 }: { profession: Profession | null; size?: number }) {
  if (!profession) return null;
  if (profession.icon) {
    return (
      <img
        className="profession-icon"
        src={profession.icon}
        alt={profession.name}
        title={profession.name}
        style={{ width: size, height: size }}
      />
    );
  }
  if (!profession.emoji) return null;
  return (
    <span className="profession-icon" title={profession.name} style={{ fontSize: size * 0.85 }}>
      {profession.emoji}
    </span>
  );
}
