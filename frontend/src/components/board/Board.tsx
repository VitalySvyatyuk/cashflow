import { motion } from "motion/react";
import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { useBoard } from "../../api/board";
import type { BoardCell, GameState, PlayerState, Track } from "../../api/types";
import { textOn } from "../../lib/format";
import { onGameEvent } from "../../store/game";
import {
  CENTER,
  RINGS,
  SIZE,
  TOKEN_RADIUS,
  dreamStarPoint,
  sectorPath,
  starPoints,
  tokenPoint,
} from "./geometry";
import { msUntilArrival } from "../../lib/movement";
import { STEP_MS } from "../../lib/timing";
import { useTokenSteps, type Spot } from "./useTokenSteps";
import { CELL_ICONS, iconInk, iconTransform, shade } from "./icons";

// Размер значка на клетке: малый круг шире, большой — 40 узких клеток.
const ICON_SIZE: Record<Track, number> = { rat_race: 38, fast_track: 30 };

const LANDING_SHOW_MS = 10000;

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
      // Бизнес показывается карточкой в центре поля (BusinessCard), пока игрок не решит.
      if (!player || !cell || cell.kind === "business") return;
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
  // На мечте, которую кто-то выбрал, вместо значка — звёзды цвета игроков.
  const chosenDreams = new Set(state.players.map((p) => p.dream_id));

  return (
    <div className="board">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Игровое поле">
        <defs>
          <filter id="token-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="3" stdDeviation="3" floodOpacity="0.45" />
          </filter>
          <filter id="ring-shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="6" stdDeviation="10" floodOpacity="0.5" />
          </filter>
          {state.players.map((p) => (
            <radialGradient key={p.id} id={`token-${p.id}`} cx="35%" cy="30%" r="75%">
              <stop offset="0" stopColor={shade(p.color, 0.35)} />
              <stop offset="0.6" stopColor={p.color} />
              <stop offset="1" stopColor={shade(p.color, -0.35)} />
            </radialGradient>
          ))}
        </defs>

        <g filter="url(#ring-shadow)">
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
        </g>

        {(["fast_track", "rat_race"] as Track[]).map((track) =>
          board[track].map((cell) => {
            const icon = CELL_ICONS[cell.kind];
            if (!icon || chosenDreams.has(cell.id)) return null;
            const { x, y } = tokenPoint(track, cell.position, board[track].length);
            return (
              <path
                key={`icon-${cell.id}`}
                d={icon}
                transform={iconTransform(x, y, ICON_SIZE[track])}
                fill={iconInk(cell.color)}
                className="cell-icon"
              />
            );
          }),
        )}

        {board.fast_track.map((cell) => {
          const dreamers = state.players.filter((p) => p.dream_id === cell.id);
          return dreamers.map((p, i) => {
            const { x, y } = dreamStarPoint(cell.position, board.fast_track.length, i, dreamers.length);
            return (
              <polygon
                key={`dream-${p.id}`}
                points={starPoints()}
                transform={`translate(${x.toFixed(2)} ${y.toFixed(2)})`}
                fill={p.color}
                className={`dream-star ${p.id === meId ? "dream-star-me" : ""}`}
              >
                <title>
                  Мечта игрока {p.name}: {cell.title}
                </title>
              </polygon>
            );
          });
        })}

        {currentSpot && board[currentSpot.track].length > 0 && (
          <path
            d={sectorPath(RINGS[currentSpot.track], currentSpot.position, board[currentSpot.track].length)}
            fill="none"
            stroke={current!.color}
            strokeWidth={6}
            className="cell-highlight"
          />
        )}

        <circle cx={CENTER} cy={CENTER} r={RINGS.rat_race.inner - 14} className="board-center" />
        <circle cx={CENTER} cy={CENTER} r={RINGS.rat_race.inner - 34} className="board-center-ring" />
        {/* Название видно и во время броска; прячется только под открытой карточкой. */}
        {!state.current_card && (
          <text className="board-title">
            <tspan x={CENTER} y={CENTER - 14}>
              ДЕНЕЖНЫЙ
            </tspan>
            <tspan x={CENTER} y={CENTER + 34}>
              ПОТОК
            </tspan>
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
              <Token player={player} me={player.id === meId} />
              <title>{player.name}</title>
            </motion.g>
          );
        })}
      </svg>

      <div className="board-middle">{children}</div>

      {/* Над кнопками действий внизу слева (см. .landing), а не над полем — чтобы не закрывать клетки. */}
      {landing &&
        createPortal(
          <div className="landing" key={landing.key} style={{ borderColor: landing.cell.color }}>
            <span className="chip" style={{ background: landing.player.color }} />
            <b>{landing.player.name}</b> — {landing.cell.title}
            {landing.cell.description && <div className="muted">{landing.cell.description}</div>}
          </div>,
          document.querySelector(".game-layout > footer") ?? document.body,
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
              <span className="legend-chip" style={{ background: c.color, color: iconInk(c.color) }}>
                {CELL_ICONS[c.kind] && (
                  <svg viewBox="0 -960 960 960" className="cell-icon" aria-hidden>
                    <path d={CELL_ICONS[c.kind]} fill="currentColor" />
                  </svg>
                )}
              </span>{" "}
              {c.kind_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Объёмная фишка: белый ободок (у своей — золотой), градиент и блик. */
function Token({ player, me }: { player: PlayerState; me: boolean }) {
  const r = TOKEN_RADIUS + (me ? 3 : 0);
  return (
    <>
      <g filter="url(#token-shadow)" className="token">
        <circle r={r + 3} fill={me ? "var(--felt-gold)" : "#fff"} />
        <circle r={r} fill={`url(#token-${player.id})`} />
        <ellipse cx={-r * 0.3} cy={-r * 0.38} rx={r * 0.5} ry={r * 0.3} fill="#fff" opacity={0.45} />
      </g>
      <text className="token-label" dy="0.35em" fontSize={r * 0.95} fill={textOn(player.color)}>
        {player.name.slice(0, 1).toUpperCase()}
      </text>
    </>
  );
}
