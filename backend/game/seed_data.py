"""Временные данные для разработки: профессии, карточки и клетки поля.

Карточки генерируются случайно, но с фиксированным seed — при каждом запуске
получается один и тот же набор. Позже заменим на настоящие.
"""

import random

from game.models import CardCategory, CellKind, Track

CARD_COLORS = {
    CardCategory.SMALL_DEAL: "#43a047",
    CardCategory.BIG_DEAL: "#1b5e20",
    CardCategory.MARKET: "#1565c0",
    CardCategory.DOODAD: "#d81b60",
}

CELL_COLORS = {
    CellKind.OPPORTUNITY: "#2e7d32",
    CellKind.MARKET: "#1565c0",
    CellKind.DOODAD: "#d81b60",
    CellKind.PAYCHECK: "#f9a825",
    CellKind.CHARITY: "#ef6c00",
    CellKind.BABY: "#8e24aa",
    CellKind.DOWNSIZED: "#424242",
    CellKind.CASHFLOW_DAY: "#fbc02d",
    CellKind.BUSINESS: "#00897b",
    CellKind.DREAM: "#5e35b1",
    CellKind.LOSS: "#c62828",
}


def _liabilities(mortgage, school, car, cards, retail):
    items = [
        ("Ипотека", mortgage),
        ("Кредит на обучение", school),
        ("Автокредит", car),
        ("Кредитные карты", cards),
        ("Потребительский кредит", retail),
    ]
    return [
        {"title": title, "balance": balance, "payment": payment}
        for title, (balance, payment) in items
        if balance
    ]


PROFESSIONS = [
    {
        "name": "Учитель",
        "emoji": "👩‍🏫",
        "salary": 3300,
        "taxes": 630,
        "other_expenses": 760,
        "per_child_expense": 180,
        "savings": 400,
        "liabilities": _liabilities((50000, 500), (12000, 60), (5000, 100), (3000, 90), (1000, 50)),
    },
    {
        "name": "Инженер",
        "emoji": "👷",
        "salary": 4900,
        "taxes": 1050,
        "other_expenses": 1090,
        "per_child_expense": 250,
        "savings": 400,
        "liabilities": _liabilities(
            (75000, 700), (12000, 60), (7000, 140), (4000, 120), (1000, 50)
        ),
    },
    {
        "name": "Врач",
        "emoji": "👨‍⚕️",
        "salary": 13200,
        "taxes": 3420,
        "other_expenses": 2880,
        "per_child_expense": 640,
        "savings": 400,
        "liabilities": _liabilities(
            (202000, 1900), (150000, 750), (19000, 380), (9000, 270), (1000, 50)
        ),
    },
    {
        "name": "Медсестра",
        "emoji": "👩‍⚕️",
        "salary": 3100,
        "taxes": 600,
        "other_expenses": 710,
        "per_child_expense": 170,
        "savings": 480,
        "liabilities": _liabilities((47000, 400), (6000, 30), (5000, 100), (3000, 90), (1000, 50)),
    },
    {
        "name": "Полицейский",
        "emoji": "👮",
        "salary": 3000,
        "taxes": 580,
        "other_expenses": 690,
        "per_child_expense": 160,
        "savings": 520,
        "liabilities": _liabilities((46000, 400), (0, 0), (5000, 100), (2000, 60), (1000, 50)),
    },
    {
        "name": "Секретарь",
        "emoji": "🗂️",
        "salary": 2500,
        "taxes": 460,
        "other_expenses": 570,
        "per_child_expense": 140,
        "savings": 710,
        "liabilities": _liabilities((38000, 400), (0, 0), (4000, 80), (2000, 60), (1000, 50)),
    },
    {
        "name": "Менеджер",
        "emoji": "💼",
        "salary": 4600,
        "taxes": 910,
        "other_expenses": 1000,
        "per_child_expense": 240,
        "savings": 400,
        "liabilities": _liabilities((75000, 700), (12000, 60), (6000, 120), (4000, 90), (1000, 50)),
    },
    {
        "name": "Пилот",
        "emoji": "✈️",
        "salary": 9500,
        "taxes": 2350,
        "other_expenses": 2210,
        "per_child_expense": 480,
        "savings": 400,
        "liabilities": _liabilities((90000, 1000), (0, 0), (15000, 300), (22000, 660), (1000, 50)),
    },
]

STOCKS = ["ОКЗ", "МГС", "ВКУС", "ТЕХН", "ЗЛТ"]

SMALL_PROPERTIES = ["Дом 2/1", "Дом 3/2", "Квартира-студия", "Дуплекс", "Кондоминиум"]
BIG_PROPERTIES = [
    "Многоквартирный дом",
    "Автомойка",
    "Прачечная",
    "Мини-отель",
    "Торговый павильон",
]
DOODADS = [
    "Новый смартфон",
    "Ужин в ресторане",
    "Ремонт машины",
    "Абонемент в спортзал",
    "Подарок на свадьбу друга",
    "Новый телевизор",
    "Отпуск на море",
    "Штраф за парковку",
    "Поход к стоматологу",
    "Билеты на концерт",
]
FLAVOR = [
    "Хозяин уезжает в другой город и хочет быстро продать.",
    "Рынок оживает — аналитики ждут роста.",
    "Объект требует небольшого ремонта.",
    "Сосед по офису советует не упускать шанс.",
    "Предложение действует только сегодня.",
]


def _round(value, step=100):
    return int(round(value / step) * step)


def build_cards(seed=2026):
    rnd = random.Random(seed)
    cards = []

    for symbol in STOCKS:
        price = rnd.choice([1, 5, 10, 20, 30, 40])
        cards.append(
            {
                "category": CardCategory.SMALL_DEAL,
                "title": f"Акции {symbol} по ${price}",
                "text": f"Можно купить любое количество акций {symbol} по ${price}.",
                "effect": {"type": "stock", "symbol": symbol, "price": price},
            }
        )
    for i in range(7):
        name = SMALL_PROPERTIES[i % len(SMALL_PROPERTIES)]
        cost = _round(rnd.randint(30000, 90000), 1000)
        down = _round(cost * rnd.choice([0.05, 0.1, 0.15]))
        cards.append(
            {
                "category": CardCategory.SMALL_DEAL,
                "title": f"{name} за ${cost:,}".replace(",", " "),
                "text": rnd.choice(FLAVOR),
                "effect": {
                    "type": "real_estate",
                    "property": name,
                    "cost": cost,
                    "down_payment": down,
                    "mortgage": cost - down,
                    "cashflow": _round(rnd.randint(50, 400), 10),
                },
            }
        )

    for i in range(8):
        name = BIG_PROPERTIES[i % len(BIG_PROPERTIES)]
        cost = _round(rnd.randint(150000, 900000), 5000)
        down = _round(cost * rnd.choice([0.1, 0.15, 0.2]), 1000)
        cards.append(
            {
                "category": CardCategory.BIG_DEAL,
                "title": f"{name} за ${cost:,}".replace(",", " "),
                "text": rnd.choice(FLAVOR),
                "effect": {
                    "type": "real_estate",
                    "property": name,
                    "cost": cost,
                    "down_payment": down,
                    "mortgage": cost - down,
                    "cashflow": _round(rnd.randint(800, 6000), 100),
                },
            }
        )

    for symbol in STOCKS[:4]:
        price = rnd.choice([1, 40, 50, 60])
        cards.append(
            {
                "category": CardCategory.MARKET,
                "title": f"Курс {symbol}: ${price}",
                "text": "Все владельцы акций могут продать их по этой цене.",
                "effect": {"type": "stock_price", "symbol": symbol, "price": price},
            }
        )
    for name in SMALL_PROPERTIES[:4]:
        price = _round(rnd.randint(40000, 140000), 5000)
        cards.append(
            {
                "category": CardCategory.MARKET,
                "title": f"Покупатель на «{name}»",
                "text": f"Предлагают ${price:,} за объект «{name}».".replace(",", " "),
                "effect": {"type": "sell_offer", "property": name, "price": price},
            }
        )

    for title in DOODADS:
        amount = _round(rnd.randint(50, 3000), 50)
        cards.append(
            {
                "category": CardCategory.DOODAD,
                "title": title,
                "text": f"Заплатите ${amount:,}.".replace(",", " "),
                "effect": {"type": "expense", "amount": amount},
            }
        )

    for card in cards:
        card["color"] = CARD_COLORS[card["category"]]
    return cards


RAT_RACE_PATTERN = [
    CellKind.OPPORTUNITY,
    CellKind.DOODAD,
    CellKind.OPPORTUNITY,
    CellKind.CHARITY,
    CellKind.OPPORTUNITY,
    CellKind.PAYCHECK,
    CellKind.OPPORTUNITY,
    CellKind.MARKET,
    CellKind.OPPORTUNITY,
    CellKind.DOODAD,
    CellKind.OPPORTUNITY,
    CellKind.BABY,
    CellKind.OPPORTUNITY,
    CellKind.PAYCHECK,
    CellKind.OPPORTUNITY,
    CellKind.MARKET,
    CellKind.OPPORTUNITY,
    CellKind.DOODAD,
    CellKind.OPPORTUNITY,
    CellKind.DOWNSIZED,
    CellKind.OPPORTUNITY,
    CellKind.PAYCHECK,
    CellKind.OPPORTUNITY,
    CellKind.MARKET,
]

RAT_RACE_TEXT = {
    CellKind.OPPORTUNITY: ("Возможность", "Вытяните карточку малой или крупной сделки."),
    CellKind.DOODAD: ("Траты", "Вытяните карточку трат и заплатите."),
    CellKind.CHARITY: (
        "Благотворительность",
        "Отдайте 10% дохода и бросайте два кубика следующие 3 хода.",
    ),
    CellKind.PAYCHECK: ("Зарплата", "Получите денежный поток."),
    CellKind.MARKET: ("Рынок", "Вытяните карточку рынка — возможно, кто-то купит ваш актив."),
    CellKind.BABY: ("Ребёнок", "У вас родился ребёнок: расходы растут."),
    CellKind.DOWNSIZED: ("Увольнение", "Заплатите сумму расходов и пропустите 2 хода."),
}

# Повторяющийся блок из 10 клеток скоростной дорожки.
FAST_TRACK_BLOCK = [
    CellKind.CASHFLOW_DAY,
    CellKind.BUSINESS,
    CellKind.DREAM,
    CellKind.BUSINESS,
    CellKind.LOSS,
    CellKind.BUSINESS,
    CellKind.DREAM,
    CellKind.BUSINESS,
    CellKind.CHARITY,
    CellKind.BUSINESS,
]

BUSINESSES = [
    "Пиццерия",
    "Автосервис",
    "Сеть кофеен",
    "IT-стартап",
    "Фитнес-клуб",
    "Пекарня",
    "Склад-логистика",
    "Частная школа",
    "Гостиница",
    "Торговый центр",
    "Ферма",
    "Типография",
    "Стоматология",
    "Кинотеатр",
    "Сеть химчисток",
    "Завод напитков",
    "Сеть автозаправок",
    "Рекламное агентство",
    "Горнолыжный курорт",
    "Ветеринарная клиника",
]
DREAMS = [
    "Кругосветное путешествие",
    "Яхта",
    "Собственный остров",
    "Библиотека для города",
    "Дом в горах",
    "Частный самолёт",
    "Фонд помощи детям",
    "Виноградник",
]
LOSSES = ["Налоговая проверка", "Развод", "Судебный иск", "Неудачная инвестиция"]


def build_cells(seed=2026):
    rnd = random.Random(seed)
    cells = []

    for position, kind in enumerate(RAT_RACE_PATTERN):
        title, description = RAT_RACE_TEXT[kind]
        cells.append(
            {
                "track": Track.RAT_RACE,
                "position": position,
                "kind": kind,
                "title": title,
                "description": description,
                "effect": {},
            }
        )

    businesses = iter(BUSINESSES)
    dreams = iter(DREAMS)
    losses = iter(LOSSES)
    for position in range(40):
        kind = FAST_TRACK_BLOCK[position % len(FAST_TRACK_BLOCK)]
        if kind == CellKind.BUSINESS:
            cost = _round(rnd.randint(50000, 500000), 10000)
            flow = _round(cost * rnd.uniform(0.03, 0.08), 500)
            title = next(businesses)
            description = f"Купите бизнес за ${cost:,} — +${flow:,} в месяц.".replace(",", " ")
            effect = {"cost": cost, "cashflow": flow}
        elif kind == CellKind.DREAM:
            cost = _round(rnd.randint(100000, 1000000), 50000)
            title = next(dreams)
            description = f"Мечта стоит ${cost:,}. Купите её и выиграйте.".replace(",", " ")
            effect = {"cost": cost}
        elif kind == CellKind.LOSS:
            title = next(losses)
            description = "Потеряйте половину наличных."
            effect = {"cash_share": 0.5}
        elif kind == CellKind.CHARITY:
            title = "Благотворительность"
            description = "Пожертвуйте $100 000 и бросайте 1–3 кубика 3 хода."
            effect = {"cost": 100000}
        else:
            title = "День денежного потока"
            description = "Получите месячный денежный поток бизнесов."
            effect = {}
        cells.append(
            {
                "track": Track.FAST_TRACK,
                "position": position,
                "kind": kind,
                "title": title,
                "description": description,
                "effect": effect,
            }
        )

    for cell in cells:
        cell["color"] = CELL_COLORS[cell["kind"]]
    return cells
