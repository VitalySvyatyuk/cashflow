// Повторяет game/state.py на бэкенде.

export type GameStatus = "lobby" | "running" | "paused" | "finished";
export type Phase =
  | "roll"
  | "choose_deal"
  | "card"
  | "pay"
  | "income"
  | "charity"
  | "business"
  | "dream"
  | "end_turn"
  /** Уволен: кубик не бросает, может продавать и брать/давать в долг. */
  | "skip";
export type Track = "rat_race" | "fast_track";
export type Role = "host" | "player";

export interface Statement {
  salary: number;
  passive_income: number;
  total_income: number;
  total_expenses: number;
  cashflow: number;
  can_exit_rat_race: boolean;
}

export interface Profession {
  name: string;
  emoji: string;
  /** Картинка из админки; если нет — показываем эмодзи */
  icon: string | null;
  salary: number;
  taxes: number;
  other_expenses: number;
  per_child_expense: number;
}

export interface Asset {
  id: number;
  kind: "stock" | "real_estate" | "business" | "other";
  title: string;
  description: string;
  key: string;
  quantity: number;
  cost: number;
  cashflow: number;
}

export interface Liability {
  id: number;
  title: string;
  balance: number;
  payment: number;
  asset_id: number | null;
  /** Долг другому игроку: кому и под сколько процентов в месяц. */
  lender_id: number | null;
  rate: number;
}

/** Заём, выданный другому игроку (player_id — заёмщик). */
export interface LoanGiven {
  id: number;
  player_id: number;
  balance: number;
  payment: number;
  rate: number;
}

export interface LoanOffer {
  id: number;
  lender_id: number;
  borrower_id: number;
  amount: number;
  rate: number;
}

export interface PlayerState {
  id: number;
  name: string;
  seat: number;
  color: string;
  profession: Profession | null;
  track: Track;
  position: number;
  cash: number;
  children: number;
  charity_turns: number;
  skip_turns: number;
  fast_track_income: number;
  /** Платил благотворительность в большом круге — выбор 1–3 кубиков до конца игры. */
  fast_track_charity: boolean;
  /** Сколько кубиков можно бросить сейчас (одно значение — без выбора). */
  dice_options: number[];
  statement: Statement;
  assets: Asset[];
  liabilities: Liability[];
  loans_given: LoanGiven[];
}

export interface PendingAction {
  id: number;
  player_id: number;
  kind: string;
  payload: Record<string, unknown>;
  description: string;
  status: string;
  created_at: string;
}

export interface GameEvent {
  seq: number;
  player_id: number | null;
  kind: string;
  payload: { text?: string; [key: string]: unknown };
  created_at: string;
}

export interface Card {
  id: number;
  /** Колода: по ней движок решает, когда тянуть карточку. */
  category: "small_deal" | "big_deal" | "market" | "doodad";
  /** Название и цвет категории — задаются в админке. */
  category_name: string;
  color: string;
  title: string;
  text: string;
  effect: Record<string, unknown>;
}

export interface BoardCell {
  id: number;
  track: Track;
  position: number;
  kind: string;
  color: string;
  title: string;
  description: string;
  effect: Record<string, unknown>;
}

export interface GameState {
  code: string;
  status: GameStatus;
  max_players: number;
  turn_number: number;
  current_player_id: number | null;
  phase: Phase;
  dice: number[];
  /** Сколько клеток «Доход» прошла фишка — получает кнопкой «Получить». */
  paydays: number;
  /** Кто-то отказался от недвижимости или бизнеса — сделка предложена этому игроку. */
  offer_player_id: number | null;
  /** Открыты акции: у этих игроков они есть — ждём, продадут или откажутся. */
  stock_waiting: number[];
  /** Предложения займов между игроками, ждущие ответа заёмщика. */
  loan_offers: LoanOffer[];
  current_card: Card | null;
  winner_id: number | null;
  players: PlayerState[];
  pending_actions: PendingAction[];
  events: GameEvent[];
}

// REST
export interface LobbyPlayer {
  id: number;
  name: string;
  seat: number;
  color: string;
  profession: string | null;
  profession_emoji: string;
}

export interface LobbyGame {
  code: string;
  status: GameStatus;
  max_players: number;
  turn_number: number;
  current_player_id: number | null;
  players: LobbyPlayer[];
  created_at: string;
}

export interface JoinedPlayer extends LobbyPlayer {
  token: string;
  cash: number;
}

export interface SessionUser {
  username: string;
  is_host: boolean;
}

// WebSocket: сервер → клиент
export interface Presence {
  type: "presence";
  /** id игроков, у которых открыта игра */
  players: number[];
  host: boolean;
}

export type ServerMessage =
  | { type: "hello"; role: Role; player_id: number | null; state: GameState; presence: Presence }
  | Presence
  | { type: "event"; event: GameEvent; state: GameState }
  | { type: "state"; state: GameState }
  | { type: "error"; message: string }
  | { type: "pong" };
