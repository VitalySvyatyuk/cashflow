import { motion } from "motion/react";
import { useState } from "react";

import type { Asset, Card, GameState, PlayerState } from "../../api/types";
import { money } from "../../lib/format";
import { useGame } from "../../store/game";

const CATEGORY = {
  small_deal: "Малая сделка",
  big_deal: "Крупная сделка",
  market: "Рынок",
  doodad: "Траты",
};

interface Effect {
  type?: string;
  symbol?: string;
  property?: string;
  price?: number;
  cost?: number;
  down_payment?: number;
  mortgage?: number;
  cashflow?: number;
  amount?: number;
}

/** Открытая карточка в центре поля: цифры сделки и продажа своих активов. */
export function GameCard({ state, me }: { state: GameState; me: PlayerState | null }) {
  const card = state.current_card!;
  const [collapsed, setCollapsed] = useState(false);
  const drawer = state.players.find((p) => p.id === state.current_player_id);

  if (collapsed) {
    return (
      <button className="card-chip" style={{ background: card.color }} onClick={() => setCollapsed(false)}>
        {CATEGORY[card.category]}: {card.title} ▸
      </button>
    );
  }

  return (
    <motion.div
      key={card.id}
      className="card"
      style={{ borderColor: card.color }}
      initial={{ rotateY: 90, opacity: 0, scale: 0.9 }}
      animate={{ rotateY: 0, opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div className="card-category" style={{ background: card.color }}>
        <span>{CATEGORY[card.category]}</span>
        <button className="link light" onClick={() => setCollapsed(true)} title="Свернуть, чтобы видеть поле">
          свернуть
        </button>
      </div>
      <div className="card-body">
        <h3>{card.title}</h3>
        {card.text && <p>{card.text}</p>}
        <CardNumbers effect={card.effect as Effect} />
        {drawer && <p className="muted small">Вытянул(а): {drawer.name}</p>}
        {me && state.status === "running" && <SellOptions card={card} me={me} />}
      </div>
    </motion.div>
  );
}

function CardNumbers({ effect }: { effect: Effect }) {
  const rows: [string, string][] = [];
  switch (effect.type) {
    case "stock":
      rows.push(["Цена за акцию", money(effect.price!)]);
      break;
    case "real_estate":
      rows.push(["Стоимость", money(effect.cost!)]);
      rows.push(["Первый взнос", money(effect.down_payment!)]);
      if (effect.mortgage) rows.push(["Ипотека", money(effect.mortgage)]);
      rows.push(["Денежный поток", `+${money(effect.cashflow!)} / мес`]);
      break;
    case "stock_price":
      rows.push([`Курс ${effect.symbol}`, money(effect.price!)]);
      break;
    case "sell_offer":
      rows.push([`Предлагают за «${effect.property}»`, money(effect.price!)]);
      break;
    case "expense":
      rows.push(["Заплатить", money(effect.amount!)]);
      break;
  }
  if (!rows.length) return null;
  return (
    <dl className="card-numbers">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Что игрок может продать по этой карточке — доступно всем, не только тому, чей ход. */
function SellOptions({ card, me }: { card: Card; me: PlayerState }) {
  const effect = card.effect as Effect;
  let assets: Asset[] = [];
  if (effect.type === "stock" || effect.type === "stock_price") {
    assets = me.assets.filter((a) => a.kind === "stock" && a.key === effect.symbol);
  } else if (effect.type === "sell_offer") {
    assets = me.assets.filter((a) => a.kind === "real_estate" && a.key === effect.property);
  }
  if (!assets.length) return null;

  return (
    <div className="sell">
      <div className="small">Можно продать:</div>
      {assets.map((a) =>
        a.kind === "stock" ? (
          <SellStock key={a.id} asset={a} price={effect.price!} />
        ) : (
          <SellProperty key={a.id} asset={a} me={me} price={effect.price!} />
        ),
      )}
    </div>
  );
}

function SellStock({ asset, price }: { asset: Asset; price: number }) {
  const action = useGame((s) => s.action);
  const [quantity, setQuantity] = useState(asset.quantity);
  return (
    <div className="sell-row">
      <input
        type="number"
        min={1}
        max={asset.quantity}
        value={quantity}
        onChange={(e) => setQuantity(Math.min(asset.quantity, Math.max(1, Number(e.target.value))))}
        className="qty"
      />
      <span>
        из {asset.quantity} {asset.key} → <b>+{money(quantity * price)}</b>
      </span>
      <button onClick={() => action("sell", { asset_id: asset.id, quantity })}>Продать</button>
    </div>
  );
}

function SellProperty({ asset, me, price }: { asset: Asset; me: PlayerState; price: number }) {
  const action = useGame((s) => s.action);
  const mortgage = me.liabilities.find((l) => l.asset_id === asset.id)?.balance ?? 0;
  const net = price - mortgage;
  return (
    <div className="sell-row">
      <span>
        «{asset.title}»{mortgage ? ` (ипотека ${money(mortgage)})` : ""} →{" "}
        <b className={net < 0 ? "negative" : ""}>
          {net >= 0 ? "+" : ""}
          {money(net)}
        </b>
      </span>
      <button onClick={() => action("sell", { asset_id: asset.id })}>Продать</button>
    </div>
  );
}
