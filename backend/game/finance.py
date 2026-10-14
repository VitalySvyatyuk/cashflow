"""Финансовый отчёт игрока и денежные операции."""

from dataclasses import asdict, dataclass

from game.models import Liability

BANK_LOAN_TITLE = "Банковский кредит"
BANK_LOAN_STEP = 1000
BANK_LOAN_RATE = 0.1  # платёж в месяц от суммы кредита
MAX_CHILDREN = 3


@dataclass
class Statement:
    salary: int
    passive_income: int
    total_income: int
    total_expenses: int
    cashflow: int

    @property
    def can_exit_rat_race(self):
        return self.passive_income > self.total_expenses

    def as_dict(self):
        return asdict(self) | {"can_exit_rat_race": self.can_exit_rat_race}


def statement(player):
    profession = player.profession
    passive = sum(a.cashflow for a in player.assets.all())
    salary = profession.salary if profession else 0
    expenses = sum(li.payment for li in player.liabilities.all())
    if profession:
        expenses += (
            profession.taxes
            + profession.other_expenses
            + player.children * profession.per_child_expense
        )
    total_income = salary + passive
    return Statement(
        salary=salary,
        passive_income=passive,
        total_income=total_income,
        total_expenses=expenses,
        cashflow=total_income - expenses,
    )


def round_up_loan(amount):
    return -(-amount // BANK_LOAN_STEP) * BANK_LOAN_STEP


def take_bank_loan(player, amount):
    if amount <= 0 or amount % BANK_LOAN_STEP:
        raise ValueError(amount)
    loan, _ = Liability.objects.get_or_create(
        player=player,
        title=BANK_LOAN_TITLE,
        asset=None,
        defaults={"balance": 0, "payment": 0},
    )
    loan.balance += amount
    loan.payment = int(loan.balance * BANK_LOAN_RATE)
    loan.save()
    player.cash += amount
    player.save(update_fields=["cash"])


def pay(player, amount):
    """Обязательный платёж: если наличных не хватает — берёт кредит. Возвращает сумму кредита."""
    loan = round_up_loan(amount - player.cash) if amount > player.cash else 0
    if loan:
        take_bank_loan(player, loan)
    player.cash -= amount
    player.save(update_fields=["cash"])
    return loan


def receive(player, amount):
    player.cash += amount
    player.save(update_fields=["cash"])
