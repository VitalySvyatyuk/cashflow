import { motion } from "motion/react";
import { useEffect, useState, type ReactNode } from "react";

import { useBoard } from "../../api/board";
import type { BoardCell, GameState, PlayerState, Track } from "../../api/types";
import { textOn } from "../../lib/format";
import { onGameEvent } from "../../store/game";
import { CENTER, RINGS, SIZE, TOKEN_RADIUS, sectorPath, tokenPoint } from "./geometry";
import { msUntilArrival } from "../../lib/movement";
import { STEP_MS } from "../../lib/timing";
import { useTokenSteps, type Spot } from "./useTokenSteps";

const LANDING_SHOW_MS = 5000;

interface Landing {
  key: number;
  player: PlayerState;
  cell: BoardCell;
}

interface Props {
  state: GameState;
  meId?: number | null;
  /** Содержимое центра поля (кубики, карточка). */
  children?: ReactNode;
}

export function Board({ state, meId, children }: Props) {
  const board = useBoard();
  const overrides = useTokenSteps();
  const [landing, setLanding] = useState<Landing | null>(null);

  // Описание клетки — когда фишка до неё дошла.
  useEffect(() => {
    if (!board) return;
    let timers: number[] = [];
    const unsubscribe = onGameEvent((event, s) => {
      if (event.kind !== "landed" || event.player_id == null) return;
      const player = s.players.find((p) => p.id === event.player_id);
      const cell = [...board.rat_race, ...board.fast_track].find(
        (c) => c.id === event.payload.cell_id,
      );
      if (!player || !cell) return;
      const wait = msUntilArrival(player.id);
      const show = window.setTimeout(() => setLanding({ key: event.seq, player, cell }), wait);
      const hide = window.setTimeout(
        () => setLanding((l) => (l?.key === event.seq ? null : l)),
        wait + LANDING_SHOW_MS,
      );
      timers.push(show, hide);
    });
    return () => {
      unsubscribe();
      timers.forEach((t) => window.clearTimeout(t));
      timers = [];
    };
  }, [board]);

  if (!board) return <div className="board-loading">Загрузка поля…</div>;

  const spotOf = (p: PlayerState): Spot => overrides[p.id] ?? { track: p.track, position: p.position };
  const spots = state.players.map((p) => ({ player: p, spot: spotOf(p) }));
  const groups = new Map<string, number[]>();
  for (const { player, spot } of spots) {
    const key = `${spot.track}:${spot.position}`;
    groups.set(key, [...(groups.get(key) ?? []), player.id]);
  }

  const current = state.players.find((p) => p.id === state.current_player_id);
  const currentSpot = current ? spotOf(current) : null;

  return (
    <div className="board">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Игровое поле">
        {(["fast_track", "rat_race"] as Track[]).map((track) =>
          board[track].map((cell) => (
            <path
              key={cell.id}
              d={sectorPath(RINGS[track], cell.position, board[track].length)}
              fill={cell.color}
              className="cell"
            >
              <title>{cell.title}</title>
            </path>
          )),
        )}

        {currentSpot && board[currentSpot.track].length > 0 && (
          <path
            d={sectorPath(RINGS[currentSpot.track], currentSpot.position, board[currentSpot.track].length)}
            fill="none"
            stroke={current!.color}
            strokeWidth={6}
            className="cell-highlight"
          />
        )}

        <circle cx={CENTER} cy={CENTER} r={RINGS.rat_race.inner - 12} className="board-center" />
        {!state.dice.length && !state.current_card && (
          <text x={CENTER} y={CENTER} dy="0.35em" className="board-title">
            ДЕНЕЖНЫЙ ПОТОК
          </text>
        )}

        {spots.map(({ player, spot }) => {
          const group = groups.get(`${spot.track}:${spot.position}`)!;
          const count = board[spot.track].length || 1;
          const { x, y } = tokenPoint(spot.track, spot.position, count, group.indexOf(player.id), group.length);
          return (
            <motion.g
              key={player.id}
              initial={false}
              animate={{ x, y }}
              transition={{ duration: (STEP_MS - 40) / 1000, ease: "easeOut" }}
            >
              <circle
                r={TOKEN_RADIUS + (player.id === meId ? 3 : 0)}
                fill={player.color}
                className={`token ${player.id === meId ? "token-me" : ""}`}
              />
              <text className="token-label" dy="0.35em" fill={textOn(player.color)}>
                {player.name.slice(0, 1).toUpperCase()}
              </text>
              <title>{player.name}</title>
            </motion.g>
          );
        })}
      </svg>

      <div className="board-middle">{children}</div>

      {landing && (
        <div className="landing" key={landing.key} style={{ borderColor: landing.cell.color }}>
          <span className="chip" style={{ background: landing.player.color }} />
          <b>{landing.player.name}</b> — {landing.cell.title}
          {landing.cell.description && <div className="muted">{landing.cell.description}</div>}
        </div>
      )}

      <Legend board={board} />
    </div>
  );
}

/** Клетки показаны только цветом — подсказка, какой цвет что значит. */
function Legend({ board }: { board: Record<Track, BoardCell[]> }) {
  const [open, setOpen] = useState(false);
  const kinds = new Map<string, BoardCell>();
  for (const cell of [...board.rat_race, ...board.fast_track]) {
    if (!kinds.has(cell.kind)) kinds.set(cell.kind, cell);
  }
  return (
    <div className="legend">
      <button className="link" onClick={() => setOpen((o) => !o)}>
        {open ? "скрыть" : "что значат цвета?"}
      </button>
      {open && (
        <ul>
          {[...kinds.values()].map((c) => (
            <li key={c.kind}>
              <span className="chip" style={{ background: c.color }} /> {KIND_NAMES[c.kind] ?? c.title}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const KIND_NAMES: Record<string, string> = {
  opportunity: "Возможность",
  market: "Рынок",
  doodad: "Траты",
  paycheck: "Зарплата",
  charity: "Благотворительность",
  baby: "Ребёнок",
  downsized: "Увольнение",
  cashflow_day: "День денежного потока",
  business: "Бизнес",
  dream: "Мечта",
  loss: "Потеря",
};
