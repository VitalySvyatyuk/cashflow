import { motion } from "motion/react";

import { useBoard } from "../../api/board";
import type { GameState } from "../../api/types";
import { money, signed } from "../../lib/format";

/** Бизнес большого круга в центре поля: висит, пока игрок не купит или не откажется. */
export function BusinessCard({ state }: { state: GameState }) {
  const board = useBoard();
  const player = state.players.find((p) => p.id === state.current_player_id);
  const cell = player && board?.[player.track].find((c) => c.position === player.position);
  if (!player || !cell) return null;
  const effect = cell.effect as { cost?: number; cashflow?: number };
  return (
    <motion.div
      key={cell.id}
      className="card"
      style={{ borderColor: cell.color }}
      initial={{ rotateY: 90, opacity: 0, scale: 0.9 }}
      animate={{ rotateY: 0, opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div className="card-category" style={{ background: cell.color }}>
        <span>{cell.kind_name}</span>
      </div>
      <div className="card-body">
        <h3>{cell.title}</h3>
        {cell.description && <p>{cell.description}</p>}
        <dl className="card-numbers">
          <div>
            <dt>Стоимость</dt>
            <dd>{money(effect.cost ?? 0)}</dd>
          </div>
          <div>
            <dt>Денежный поток</dt>
            <dd>{signed(effect.cashflow ?? 0)} в месяц</dd>
          </div>
        </dl>
        <p className="muted small">Решает: {player.name}</p>
      </div>
    </motion.div>
  );
}
