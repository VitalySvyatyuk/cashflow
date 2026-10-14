import type { Card } from "../api/types";

const CATEGORY = {
  small_deal: "Малая сделка",
  big_deal: "Крупная сделка",
  market: "Рынок",
  doodad: "Траты",
};

export function CardView({ card }: { card: Card }) {
  return (
    <div className="card" style={{ borderColor: card.color }}>
      <div className="card-category" style={{ background: card.color }}>
        {CATEGORY[card.category]}
      </div>
      <h3>{card.title}</h3>
      <p>{card.text}</p>
    </div>
  );
}
