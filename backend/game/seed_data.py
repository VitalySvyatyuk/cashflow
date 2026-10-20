"""Данные игры: профессии, карточки и клетки поля. Все суммы — в рублях.

Профессии — настоящие. Карточки и клетки пока генерируются случайно, но с фиксированным
seed — при каждом запуске получается один и тот же набор. Позже заменим на настоящие.
"""

import random

from game.finance import rub
from game.models import CardCategory, CardKind, CellKind, Track

# Категории карточек при первом заполнении: название и цвет колоды.
CATEGORY_NAMES = {
    CardCategory.SMALL_DEAL: "Малая сделка",
    CardCategory.BIG_DEAL: "Крупная сделка",
    CardCategory.MARKET: "Рынок",
    CardCategory.DOODAD: "Траты",
}
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


def _liabilities(mortgage, education, car, card, small):
    """Пассивы профессии: (сумма долга, платёж в месяц). Нулевые долги не создаём."""
    items = [
        ("Ипотека", mortgage),
        ("Кредит на образование", education),
        ("Кредит на машину", car),
        ("Кредитная карточка", card),
        ("Мелкие кредиты", small),
    ]
    return [
        {"title": title, "balance": balance, "payment": payment}
        for title, (balance, payment) in items
        if balance
    ]


def _profession(name, emoji, salary, taxes, other, per_child, savings, *liabilities):
    return {
        "name": name,
        "emoji": emoji,
        "salary": salary,
        "taxes": taxes,
        "other_expenses": other,
        "per_child_expense": per_child,
        "savings": savings,
        "liabilities": _liabilities(*liabilities),
    }


# Карточки профессий 01–12 в рублях (docs/Карточки_профессий_01-12_рубли.md).
# Пассивы: ипотека, кредит на образование, на машину, кредитная карточка, мелкие кредиты.
# fmt: off
PROFESSIONS = [
    _profession(
        "Секретарь", "🗂️", 25000, 4600, 5700, 1400, 15900,
        (380000, 4000), (0, 0), (40000, 800), (20000, 600), (10000, 500),
    ),
    _profession(
        "Менеджер", "💼", 46000, 9100, 10000, 2400, 20700,
        (750000, 7000), (120000, 600), (60000, 1200), (30000, 900), (10000, 500),
    ),
    _profession(
        "Водитель грузовика", "🚚", 25000, 4600, 5700, 1400, 16300,
        (380000, 4000), (0, 0), (40000, 800), (20000, 600), (10000, 500),
    ),
    _profession(
        "Пилот авиалиний", "✈️", 95000, 23500, 22100, 4800, 30000,
        (1430000, 13300), (0, 0), (150000, 3000), (220000, 6600), (10000, 500),
    ),
    _profession(
        "Автомеханик", "🔧", 20000, 3600, 4500, 1100, 13900,
        (310000, 3000), (0, 0), (30000, 600), (20000, 600), (10000, 500),
    ),
    _profession(
        "Адвокат", "⚖️", 75000, 18300, 16500, 3800, 24800,
        (1150000, 11000), (780000, 3900), (110000, 2200), (60000, 1800), (10000, 500),
    ),
    _profession(
        "Инженер", "👷", 49000, 10500, 10900, 2500, 20900,
        (750000, 7000), (120000, 600), (70000, 1400), (40000, 1200), (10000, 500),
    ),
    _profession(
        "Учитель", "👩‍🏫", 33000, 6300, 7600, 1800, 15100,
        (500000, 5000), (120000, 600), (50000, 1000), (30000, 900), (10000, 500),
    ),
    _profession(
        "Дворник", "🧹", 16000, 2800, 3000, 700, 12100,
        (200000, 2000), (0, 0), (40000, 600), (20000, 600), (10000, 500),
    ),
    _profession(
        "Медсестра", "👩‍⚕️", 31000, 6000, 7100, 1700, 16000,
        (470000, 4000), (60000, 300), (50000, 1000), (30000, 900), (10000, 500),
    ),
    _profession(
        "Врач", "👨‍⚕️", 132000, 34200, 28800, 6400, 39500,
        (2020000, 19000), (1500000, 7500), (190000, 3800), (90000, 2700), (10000, 500),
    ),
    _profession(
        "Офицер полиции", "👮", 30000, 5800, 6900, 1600, 16400,
        (460000, 4000), (0, 0), (50000, 1000), (20000, 600), (10000, 500),
    ),
]
# fmt: on

# Старые названия — чтобы make seed переименовал профессии, а не завёл дубли.
RENAMED_PROFESSIONS = {"Полицейский": "Офицер полиции", "Пилот": "Пилот авиалиний"}

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


# Плексы считаются по квартирам: покупатель платит за каждую квартиру.
PLEX_TAIL = "Купите сами или продайте это право другому игроку."
PLEXES = [
    # (объект, квартир, стоимость, взнос, поток, текст)
    (
        "Дуплекс", 2, 60000, 6000, 300,
        "Ухоженный дуплекс в хорошем районе: владелец переезжает и продаёт. "
        f"{PLEX_TAIL} ROI 60 %, можно продать за 50 000–80 000 ₽.",
    ),
    (
        "4-плекс", 4, 80000, 20000, 400,
        "Новый 4-плекс в растущем районе, прежний владелец не заплатил налоги. "
        f"{PLEX_TAIL} ROI 24 %, можно продать за 100 000–140 000 ₽.",
    ),
    (
        "8-плекс", 8, 220000, 40000, 1700,
        "Владелец продаёт 8-плекс по разумной цене, ипотека уже согласована — "
        f"нужен только первый взнос. {PLEX_TAIL} ROI 51 %, можно продать за 200 000–280 000 ₽.",
    ),
]  # fmt: skip


def build_plex_cards():
    cards = [
        {
            "category": CardCategory.BIG_DEAL,
            "title": f"{name} на продажу",
            "text": text,
            "kind": CardKind.REAL_ESTATE,
            "property_name": name,
            "units": units,
            "cost": cost,
            "down_payment": down,
            "mortgage": cost - down,
            "cashflow": flow,
        }
        for name, units, cost, down, flow, text in PLEXES
    ]
    cards.append(
        {
            "category": CardCategory.MARKET,
            "title": "Покупатель многоквартирных домов",
            "text": "Покупатель платит 25 000 ₽ за каждую квартиру в дуплексах, 4-плексах "
            "и 8-плексах и сам финансирует сделку. Продать может любой игрок; ипотека "
            "гасится из выручки, денежный поток объекта пропадает.",
            "kind": CardKind.SELL_OFFER,
            "property_name": ", ".join(name for name, *_ in PLEXES),
            "price": 25000,
            "per_unit": True,
        }
    )
    return cards


# Рост дохода бизнеса: прибавка к потоку каждого бизнеса у всех игроков.
BUSINESS_BOOSTS = [
    (
        400,
        "Крупная компания взялась распространять продукцию вашего бизнеса — продажи выросли "
        "в 2,5 раза. Хлопот прибавилось, зато чистая прибыль выросла.",
    ),
    (
        250,
        "Ваш бизнес получил отраслевую награду за инновационный продукт, и продажи удвоились. "
        "Времени уходит больше, зато чистая прибыль выросла.",
    ),
]


def build_business_boosts():
    return [
        {
            "category": CardCategory.MARKET,
            "title": f"Положение мелкого бизнеса улучшается (+{rub(amount)})",
            "text": f"{text} Касается каждого игрока: поток каждого его бизнеса растёт "
            f"на {rub(amount)} в месяц.",
            "kind": CardKind.BUSINESS_BOOST,
            "cashflow": amount,
        }
        for amount, text in BUSINESS_BOOSTS
    ]


# Ущерб: платит только вытянувший, если у него есть такой объект, — один раз.
DAMAGES = [
    (
        "Жилец наносит вред вашей собственности",
        "Дом, Квартира, Многоквартирный дом, Дуплекс, 4-плекс, 8-плекс",
        1000,
        "Жилец потерял работу, перестал платить, а после выселения оказалось, что он испортил "
        "квартиру. Страховка покрыла почти всё, остальное — из вашего кармана.",
    ),
    (
        "Прорыв канализации",
        "8-плекс",
        2000,
        "Вода заливает все квартиры вашего 8-плекса — нужна новая канализационная труба. "
        "Если 8-плексов несколько, платите только за один.",
    ),
]


def build_damage_cards():
    return [
        {
            "category": CardCategory.MARKET,
            "title": title,
            "text": f"{text} Платит только тот, кто вытянул карточку; не хватает наличных — "
            "банк даст кредит.",
            "kind": CardKind.PROPERTY_DAMAGE,
            "property_name": properties,
            "amount": amount,
        }
        for title, properties, amount, text in DAMAGES
    ]


def _round(value, step=100):
    return int(round(value / step) * step)


def build_cards(seed=2026):
    rnd = random.Random(seed)
    cards = []

    for symbol in STOCKS:
        price = rnd.choice([10, 50, 100, 200, 300, 400])
        cards.append(
            {
                "category": CardCategory.SMALL_DEAL,
                "title": f"Акции {symbol} по {rub(price)}",
                "text": f"Можно купить любое количество акций {symbol} по {rub(price)}.",
                "kind": CardKind.STOCK,
                "symbol": symbol,
                "price": price,
            }
        )
    for i in range(7):
        name = SMALL_PROPERTIES[i % len(SMALL_PROPERTIES)]
        cost = _round(rnd.randint(300_000, 900_000), 10_000)
        down = _round(cost * rnd.choice([0.05, 0.1, 0.15]), 1000)
        cards.append(
            {
                "category": CardCategory.SMALL_DEAL,
                "title": f"{name} за {rub(cost)}",
                "text": rnd.choice(FLAVOR),
                "kind": CardKind.REAL_ESTATE,
                "property_name": name,
                "cost": cost,
                "down_payment": down,
                "mortgage": cost - down,
                "cashflow": _round(rnd.randint(500, 4000), 100),
            }
        )

    for i in range(8):
        name = BIG_PROPERTIES[i % len(BIG_PROPERTIES)]
        cost = _round(rnd.randint(1_500_000, 9_000_000), 50_000)
        down = _round(cost * rnd.choice([0.1, 0.15, 0.2]), 10_000)
        cards.append(
            {
                "category": CardCategory.BIG_DEAL,
                "title": f"{name} за {rub(cost)}",
                "text": rnd.choice(FLAVOR),
                "kind": CardKind.REAL_ESTATE,
                "property_name": name,
                "cost": cost,
                "down_payment": down,
                "mortgage": cost - down,
                "cashflow": _round(rnd.randint(8000, 60_000), 1000),
            }
        )

    for symbol in STOCKS[:4]:
        price = rnd.choice([10, 400, 500, 600])
        cards.append(
            {
                "category": CardCategory.MARKET,
                "title": f"Курс {symbol}: {rub(price)}",
                "text": "Все владельцы акций могут продать их по этой цене.",
                "kind": CardKind.STOCK_PRICE,
                "symbol": symbol,
                "price": price,
            }
        )
    for name in SMALL_PROPERTIES[:4]:
        price = _round(rnd.randint(400_000, 1_400_000), 50_000)
        cards.append(
            {
                "category": CardCategory.MARKET,
                "title": f"Покупатель на «{name}»",
                "text": f"Предлагают {rub(price)} за объект «{name}».",
                "kind": CardKind.SELL_OFFER,
                "property_name": name,
                "price": price,
            }
        )

    for title in DOODADS:
        amount = _round(rnd.randint(500, 30_000), 500)
        cards.append(
            {
                "category": CardCategory.DOODAD,
                "title": title,
                "text": f"Заплатите {rub(amount)}.",
                "kind": CardKind.EXPENSE,
                "amount": amount,
            }
        )

    return cards + build_plex_cards() + build_business_boosts() + build_damage_cards()


def build_categories():
    return [
        {"deck": deck, "name": CATEGORY_NAMES[deck], "color": CARD_COLORS[deck]}
        for deck in CardCategory
    ]


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

BABY_TEXT = "Поздравляю, у вас родился ребёнок, и государство дарит вам подарок!"
RAT_RACE_TEXT = {
    CellKind.OPPORTUNITY: ("Возможность", "Вытяните карточку малой или крупной сделки."),
    CellKind.DOODAD: ("Траты", "Вытяните карточку трат и заплатите."),
    CellKind.CHARITY: (
        "Благотворительность",
        "Отдайте 10% дохода и бросайте два кубика следующие 3 хода.",
    ),
    CellKind.PAYCHECK: ("Доход", "Получите месячный денежный поток."),
    CellKind.MARKET: ("Рынок", "Вытяните карточку рынка — возможно, кто-то купит ваш актив."),
    CellKind.BABY: ("Ребёнок", BABY_TEXT),
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
    CellKind.DREAM,
    CellKind.BUSINESS,
]
# Благотворительность в большом круге одна — на месте мечты в первом блоке.
FAST_TRACK_CHARITY_POSITION = 8
FAST_TRACK_PATTERN = [
    CellKind.CHARITY if position == FAST_TRACK_CHARITY_POSITION else kind
    for position, kind in enumerate(FAST_TRACK_BLOCK * 4)
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
# Мечты закреплены за клетками большого круга по порядку и одинаковы во всех играх.
DREAMS = [
    (
        "Путешествие мечты",
        "Отправиться в любую точку мира по программе «всё включено»: перелёт, "
        "лучшие отели, экскурсии и отдых без забот.",
        1_000_000,
    ),
    (
        "Детский образовательный центр",
        "Открыть центр, где дети смогут заниматься наукой, творчеством "
        "и изобретательством, раскрывая свои способности.",
        1_250_000,
    ),
    (
        "Восстановить лес",
        "Высадить лес на месте вырубки или пожара и обеспечить уход за деревьями, "
        "пока они не окрепнут.",
        2_500_000,
    ),
    (
        "Благотворительный фонд",
        "Создать фонд помощи семьям в трудной ситуации: оплачивать лечение, "
        "обеспечивать жильём и помогать вернуться к самостоятельной жизни.",
        2_000_000,
    ),
    (
        "Центр спасения морских животных",
        "Открыть центр, где пострадавших дельфинов, тюленей и черепах будут лечить "
        "и возвращать в естественную среду.",
        1_000_000,
    ),
    (
        "Научный центр борьбы с раком и ВИЧ",
        "Финансировать исследования и разработку новых методов лечения, объединив учёных и врачей.",
        2_250_000,
    ),
    (
        "Стать мэром своего города",
        "Победить на выборах и воплотить свою программу: благоустроить улицы, "
        "создать парки и сделать город удобнее для жителей.",
        1_250_000,
    ),
    (
        "Дом мечты",
        "Построить дом в любимом месте, обустроить его по своему вкусу и создать "
        "пространство, где хочется жить всей семьёй.",
        1_000_000,
    ),
    (
        "Полёт в космос",
        "Пройти подготовку и отправиться в космическое путешествие, чтобы увидеть "
        "Землю с орбиты и испытать невесомость.",
        2_000_000,
    ),
    (
        "Собственный фильм",
        "Собрать съёмочную команду, снять фильм по своей истории и устроить его "
        "премьеру на большом экране.",
        1_250_000,
    ),
    (
        "Покорить Эверест",
        "Пройти подготовку и отправиться с опытной командой к вершине самой высокой горы мира.",
        1_000_000,
    ),
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
            }
        )

    businesses = iter(BUSINESSES)
    dreams = iter(DREAMS)
    losses = iter(LOSSES)
    for position, kind in enumerate(FAST_TRACK_PATTERN):
        if kind == CellKind.BUSINESS:
            cost = _round(rnd.randint(500_000, 5_000_000), 100_000)
            flow = _round(cost * rnd.uniform(0.03, 0.08), 5000)
            title = next(businesses)
            description = f"Купите бизнес за {rub(cost)} — +{rub(flow)} в месяц."
            params = {"cost": cost, "cashflow": flow}
        elif kind == CellKind.DREAM:
            title, description, cost = next(dreams)
            params = {"cost": cost}
        elif kind == CellKind.LOSS:
            title = next(losses)
            description = "Потеряйте половину наличных."
            params = {"loss_percent": 50}
        elif kind == CellKind.CHARITY:
            title = "Благотворительность"
            description = (
                f"Пожертвуйте {rub(1_000_000)} — до конца игры можно бросать 1, 2 или 3 кубика."
            )
            params = {"cost": 1_000_000}
        else:
            title = "День денежного потока"
            description = "Получите месячный денежный поток бизнесов."
            params = {}
        cells.append(
            {
                "track": Track.FAST_TRACK,
                "position": position,
                "kind": kind,
                "title": title,
                "description": description,
            }
            | params
        )

    return cells


def build_cell_types():
    return [{"kind": kind, "color": CELL_COLORS[kind]} for kind in CellKind]
