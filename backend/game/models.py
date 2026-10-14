import secrets
import uuid

from django.conf import settings
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

MAX_PLAYERS = 6

# Код игры — 4 цифры: легко продиктовать голосом и ввести на планшете.
GAME_CODE_ALPHABET = "0123456789"
GAME_CODE_LENGTH = 4

PLAYER_COLORS = ["#e53935", "#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00"]


def generate_game_code():
    return "".join(secrets.choice(GAME_CODE_ALPHABET) for _ in range(GAME_CODE_LENGTH))


class Track(models.TextChoices):
    RAT_RACE = "rat_race", "Крысиные бега"
    FAST_TRACK = "fast_track", "Скоростная дорожка"


class Profession(models.Model):
    """Карточка профессии — стартовый финансовый отчёт игрока."""

    name = models.CharField("название", max_length=100, unique=True)
    salary = models.PositiveIntegerField("зарплата")
    taxes = models.PositiveIntegerField("налоги")
    other_expenses = models.PositiveIntegerField("прочие расходы")
    per_child_expense = models.PositiveIntegerField("расход на ребёнка")
    savings = models.PositiveIntegerField("сбережения")
    # [{"title": "Ипотека", "balance": 75000, "payment": 700}, ...]
    liabilities = models.JSONField("пассивы", default=list, blank=True)
    emoji = models.CharField("эмодзи", max_length=16, blank=True, help_text="Например 👩‍🏫")
    icon = models.FileField(
        "картинка",
        upload_to="professions/",
        blank=True,
        # SVG не принимаем: в нём может быть скрипт.
        validators=[FileExtensionValidator(["png", "jpg", "jpeg", "webp"])],
        help_text="PNG, JPG или WEBP, лучше квадратная. Если есть — показывается вместо эмодзи.",
    )

    class Meta:
        verbose_name = "профессия"
        verbose_name_plural = "профессии"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CardCategory(models.TextChoices):
    SMALL_DEAL = "small_deal", "Малая сделка"
    BIG_DEAL = "big_deal", "Крупная сделка"
    MARKET = "market", "Рынок"
    DOODAD = "doodad", "Траты"


class Card(models.Model):
    category = models.CharField("категория", max_length=20, choices=CardCategory.choices)
    color = models.CharField("цвет", max_length=7, help_text="HEX, например #43a047")
    title = models.CharField("название", max_length=200)
    text = models.TextField("текст", blank=True)
    # Параметры для движка: тип сделки, цена, взнос, денежный поток и т.п.
    effect = models.JSONField("эффект", default=dict, blank=True)
    is_active = models.BooleanField("в колоде", default=True)

    class Meta:
        verbose_name = "карточка"
        verbose_name_plural = "карточки"
        ordering = ["category", "title"]
        constraints = [
            models.UniqueConstraint(fields=["category", "title"], name="card_unique_title"),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"


class CellKind(models.TextChoices):
    # Крысиные бега
    OPPORTUNITY = "opportunity", "Возможность"
    MARKET = "market", "Рынок"
    DOODAD = "doodad", "Траты"
    PAYCHECK = "paycheck", "Зарплата"
    CHARITY = "charity", "Благотворительность"
    BABY = "baby", "Ребёнок"
    DOWNSIZED = "downsized", "Увольнение"
    # Скоростная дорожка
    CASHFLOW_DAY = "cashflow_day", "День денежного потока"
    BUSINESS = "business", "Бизнес"
    DREAM = "dream", "Мечта"
    LOSS = "loss", "Потеря"


class BoardCell(models.Model):
    track = models.CharField("дорожка", max_length=20, choices=Track.choices)
    position = models.PositiveSmallIntegerField("позиция")
    kind = models.CharField("тип", max_length=20, choices=CellKind.choices)
    color = models.CharField("цвет", max_length=7)
    title = models.CharField("название", max_length=200)
    description = models.TextField("описание", blank=True)
    # Для клеток скоростной дорожки: стоимость бизнеса, прибавка к потоку и т.п.
    effect = models.JSONField("эффект", default=dict, blank=True)

    class Meta:
        verbose_name = "клетка поля"
        verbose_name_plural = "клетки поля"
        ordering = ["track", "position"]
        constraints = [
            models.UniqueConstraint(fields=["track", "position"], name="cell_unique_position"),
        ]

    def __str__(self):
        return f"{self.get_track_display()} #{self.position}: {self.title}"


class GameQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(status=Game.Status.FINISHED)

    def by_code(self, code):
        """Игра по коду: незавершённая, а если такой нет — самая свежая."""
        code = code.strip()
        return (
            self.filter(code=code)
            .order_by(models.Case(models.When(status="finished", then=1), default=0), "-created_at")
            .first()
        )


class Game(models.Model):
    class Status(models.TextChoices):
        LOBBY = "lobby", "Сбор игроков"
        RUNNING = "running", "Идёт"
        PAUSED = "paused", "Заморожена"
        FINISHED = "finished", "Завершена"

    class Phase(models.TextChoices):
        ROLL = "roll", "Бросок кубиков"
        CHOOSE_DEAL = "choose_deal", "Выбор сделки"
        CARD = "card", "Открыта карточка"
        CHARITY = "charity", "Благотворительность"
        BUSINESS = "business", "Покупка бизнеса"
        DREAM = "dream", "Покупка мечты"
        END_TURN = "end_turn", "Завершение хода"

    # Уникален только среди незавершённых игр — кодов всего 10 000.
    code = models.CharField("код", max_length=GAME_CODE_LENGTH, db_index=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hosted_games",
        verbose_name="ведущий",
    )
    max_players = models.PositiveSmallIntegerField(
        "игроков",
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_PLAYERS)],
    )
    status = models.CharField("статус", max_length=20, choices=Status.choices, default=Status.LOBBY)
    current_player = models.ForeignKey(
        "Player",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="чей ход",
    )
    turn_number = models.PositiveIntegerField("номер хода", default=0)
    phase = models.CharField("фаза хода", max_length=20, choices=Phase.choices, default=Phase.ROLL)
    dice = models.JSONField("последний бросок", default=list, blank=True)
    current_card = models.ForeignKey(
        "Card",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="открытая карточка",
    )
    winner = models.ForeignKey(
        "Player",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="победитель",
    )
    created_at = models.DateTimeField("создана", auto_now_add=True)
    started_at = models.DateTimeField("начата", null=True, blank=True)
    finished_at = models.DateTimeField("завершена", null=True, blank=True)

    objects = GameQuerySet.as_manager()

    class Meta:
        verbose_name = "игра"
        verbose_name_plural = "игры"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_players__gte=1, max_players__lte=MAX_PLAYERS),
                name="game_max_players_range",
            ),
            models.UniqueConstraint(
                fields=["code"],
                condition=~models.Q(status="finished"),
                name="game_unique_active_code",
            ),
        ]

    def __str__(self):
        return f"Игра {self.code}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._unique_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _unique_code():
        while True:
            code = generate_game_code()
            if not Game.objects.active().filter(code=code).exists():
                return code


class Player(models.Model):
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="players", verbose_name="игра"
    )
    name = models.CharField("имя", max_length=40)
    # Секрет игрока: хранится в браузере, по нему игрок переподключается.
    token = models.UUIDField("токен", default=uuid.uuid4, unique=True, editable=False)
    seat = models.PositiveSmallIntegerField("место за столом")
    color = models.CharField("цвет фишки", max_length=7)
    profession = models.ForeignKey(
        Profession,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="профессия",
    )
    track = models.CharField(
        "дорожка", max_length=20, choices=Track.choices, default=Track.RAT_RACE
    )
    position = models.PositiveSmallIntegerField("позиция", default=0)
    cash = models.IntegerField("наличные", default=0)
    children = models.PositiveSmallIntegerField("дети", default=0)
    charity_turns = models.PositiveSmallIntegerField("ходов с благотворительностью", default=0)
    skip_turns = models.PositiveSmallIntegerField("пропустить ходов", default=0)
    # Доход в «День денежного потока» на скоростной дорожке.
    fast_track_income = models.PositiveIntegerField("доход скоростной дорожки", default=0)
    joined_at = models.DateTimeField("подключился", auto_now_add=True)

    class Meta:
        verbose_name = "игрок"
        verbose_name_plural = "игроки"
        ordering = ["game", "seat"]
        constraints = [
            models.UniqueConstraint(fields=["game", "name"], name="player_unique_name"),
            models.UniqueConstraint(fields=["game", "seat"], name="player_unique_seat"),
        ]

    def __str__(self):
        return self.name


class Asset(models.Model):
    class Kind(models.TextChoices):
        STOCK = "stock", "Акции"
        REAL_ESTATE = "real_estate", "Недвижимость"
        BUSINESS = "business", "Бизнес"
        OTHER = "other", "Другое"

    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="assets", verbose_name="игрок"
    )
    kind = models.CharField("тип", max_length=20, choices=Kind.choices)
    title = models.CharField("название", max_length=200)
    # Тикер акции или тип объекта («Дом 3/2») — по нему карточки рынка находят активы.
    key = models.CharField("ключ", max_length=100, blank=True, db_index=True)
    quantity = models.PositiveIntegerField("количество", default=1)
    cost = models.PositiveIntegerField("стоимость", default=0)
    cashflow = models.IntegerField("денежный поток в месяц", default=0)
    source_card = models.ForeignKey(
        Card, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="карточка"
    )

    class Meta:
        verbose_name = "актив"
        verbose_name_plural = "активы"
        ordering = ["id"]  # иначе Postgres отдаёт изменённые строки в конце

    def __str__(self):
        return self.title


class Liability(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="liabilities", verbose_name="игрок"
    )
    title = models.CharField("название", max_length=200)
    balance = models.PositiveIntegerField("остаток долга")
    payment = models.PositiveIntegerField("платёж в месяц")
    # Пассив, привязанный к активу (ипотека на дом) — гасится при продаже актива.
    asset = models.OneToOneField(
        Asset,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="liability",
        verbose_name="актив",
    )

    class Meta:
        verbose_name = "пассив"
        verbose_name_plural = "пассивы"
        ordering = ["id"]

    def __str__(self):
        return self.title


class DeckState(models.Model):
    """Перемешанная колода одной категории в конкретной игре."""

    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="decks", verbose_name="игра"
    )
    category = models.CharField("категория", max_length=20, choices=CardCategory.choices)
    card_ids = models.JSONField("порядок карт", default=list)
    next_index = models.PositiveIntegerField("следующая карта", default=0)

    class Meta:
        verbose_name = "колода"
        verbose_name_plural = "колоды"
        constraints = [
            models.UniqueConstraint(fields=["game", "category"], name="deck_unique_category"),
        ]

    def __str__(self):
        return f"{self.game}: {self.get_category_display()}"


class PendingAction(models.Model):
    """Заявка игрока на действие, которое должен одобрить ведущий."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает ведущего"
        APPROVED = "approved", "Одобрено"
        REJECTED = "rejected", "Отклонено"
        CANCELLED = "cancelled", "Отменено игроком"

    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="pending_actions", verbose_name="игра"
    )
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="pending_actions", verbose_name="игрок"
    )
    kind = models.CharField("действие", max_length=40)
    payload = models.JSONField("параметры", default=dict, blank=True)
    description = models.CharField("описание", max_length=300, blank=True)
    status = models.CharField(
        "статус", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    comment = models.CharField("комментарий ведущего", max_length=300, blank=True)
    created_at = models.DateTimeField("создана", auto_now_add=True)
    decided_at = models.DateTimeField("решена", null=True, blank=True)

    class Meta:
        verbose_name = "заявка"
        verbose_name_plural = "заявки"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.player}: {self.kind} ({self.get_status_display()})"


class GameSnapshot(models.Model):
    """Состояние игры перед действием — для отмены последнего действия ведущим."""

    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="snapshots", verbose_name="игра"
    )
    label = models.CharField("перед действием", max_length=100)
    data = models.JSONField("данные")
    created_at = models.DateTimeField("время", auto_now_add=True)

    class Meta:
        verbose_name = "снимок"
        verbose_name_plural = "снимки"
        ordering = ["game", "-id"]

    def __str__(self):
        return f"{self.game}: {self.label}"


class GameEvent(models.Model):
    """Журнал игры: всё, что произошло, по порядку."""

    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="events", verbose_name="игра"
    )
    seq = models.PositiveIntegerField("номер")
    player = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="игрок",
    )
    kind = models.CharField("событие", max_length=40)
    payload = models.JSONField("данные", default=dict, blank=True)
    created_at = models.DateTimeField("время", auto_now_add=True)

    class Meta:
        verbose_name = "событие"
        verbose_name_plural = "журнал"
        ordering = ["game", "seq"]
        constraints = [
            models.UniqueConstraint(fields=["game", "seq"], name="event_unique_seq"),
        ]

    def __str__(self):
        return f"{self.game} #{self.seq}: {self.kind}"
