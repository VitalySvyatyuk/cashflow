import { useState } from "react";

import { LOAN_STEP } from "../lib/format";

/** Сумма в рублях, кратная шагу (кредиты — по 10 000 ₽), и кнопка действия. */
export function MoneyInput({
  label,
  step = LOAN_STEP,
  max,
  onSubmit,
}: {
  label: string;
  step?: number;
  max?: number;
  onSubmit: (amount: number) => void;
}) {
  const [amount, setAmount] = useState(step);
  const valid = amount > 0 && amount % step === 0 && (max === undefined || amount <= max);
  return (
    <span className="money-input">
      <input
        type="number"
        min={step}
        step={step}
        max={max}
        value={amount}
        onChange={(e) => setAmount(Number(e.target.value))}
      />
      ₽
      <button disabled={!valid} onClick={() => onSubmit(amount)}>
        {label}
      </button>
    </span>
  );
}
