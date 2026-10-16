import { useBoard } from "../api/board";
import type { PlayerState } from "../api/types";
import { money } from "../lib/format";
import { useGame } from "../store/game";

/** Мечты — клетки большого круга. Игрок выбирает одну; купив её там, он выигрывает. */
export function DreamPicker({ me, disabled }: { me: PlayerState; disabled: boolean }) {
  const board = useBoard();
  const send = useGame((s) => s.action);
  const dreams = board?.fast_track.filter((c) => c.kind === "dream") ?? [];
  const chosen = dreams.find((c) => c.id === me.dream_id);
  if (chosen) {
    return (
      <p className="dream-chosen">
        Ваша мечта: <b>{chosen.title}</b> — {money(Number(chosen.effect.cost ?? 0))}. На большом круге
        она отмечена звездой вашего цвета.
      </p>
    );
  }
  return (
    <div className="dreams">
      <p>
        Выберите мечту. Выйдя на большой круг, встаньте на её клетку и купите — так вы победите.
      </p>
      <ul>
        {dreams.map((c) => (
          <li key={c.id}>
            <button
              className="dream"
              disabled={disabled}
              onClick={() => send("choose_dream", { cell_id: c.id })}
            >
              <span className="dream-head">
                <b>{c.title}</b>
                <span>{money(Number(c.effect.cost ?? 0))}</span>
              </span>
              <span className="muted small">{c.description}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
