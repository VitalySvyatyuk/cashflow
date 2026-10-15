"""Карточки: категория — отдельная таблица (название, цвет), эффект — отдельные поля."""

import django.db.models.deletion
from django.db import migrations, models

NAMES = {
    "small_deal": "Малая сделка",
    "big_deal": "Крупная сделка",
    "market": "Рынок",
    "doodad": "Траты",
}
DEFAULT_COLORS = {
    "small_deal": "#43a047",
    "big_deal": "#1b5e20",
    "market": "#1565c0",
    "doodad": "#d81b60",
}
FIELDS = ["symbol", "price", "cost", "down_payment", "mortgage", "cashflow", "amount"]


def forward(apps, schema_editor):
    Card = apps.get_model("game", "Card")
    Category = apps.get_model("game", "Category")
    categories = {}
    for deck, name in NAMES.items():
        # Цвет — тот, что уже был у карточек этой колоды.
        first = Card.objects.filter(category=deck).exclude(color="").first()
        color = first.color if first else DEFAULT_COLORS[deck]
        categories[deck] = Category.objects.create(deck=deck, name=name, color=color)
    for card in Card.objects.all():
        effect = card.effect or {}
        card.category_ref = categories[card.category]
        card.kind = effect.get("type", "")
        card.property_name = effect.get("property", "")
        for field in FIELDS:
            if field in effect:
                setattr(card, field, effect[field])
        card.symbol = card.symbol or ""
        card.save()


def backward(apps, schema_editor):
    Card = apps.get_model("game", "Card")
    for card in Card.objects.select_related("category_ref"):
        effect = {"type": card.kind}
        if card.property_name:
            effect["property"] = card.property_name
        for field in FIELDS:
            value = getattr(card, field)
            if value not in (None, ""):
                effect[field] = value
        card.effect = effect
        card.category = card.category_ref.deck
        card.color = card.category_ref.color
        card.save()


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0015_skip_phase"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "deck",
                    models.CharField(
                        choices=[
                            ("small_deal", "Малая сделка"),
                            ("big_deal", "Крупная сделка"),
                            ("market", "Рынок"),
                            ("doodad", "Траты"),
                        ],
                        max_length=20,
                        unique=True,
                        verbose_name="колода",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="название")),
                ("color", models.CharField(default="#757575", max_length=7, verbose_name="цвет")),
            ],
            options={
                "verbose_name": "категория карточек",
                "verbose_name_plural": "категории карточек",
                "ordering": ["id"],
            },
        ),
        migrations.AddField(
            model_name="card",
            name="category_ref",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to="game.category"
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="kind",
            field=models.CharField(
                choices=[
                    ("stock", "Акции: можно купить"),
                    ("real_estate", "Недвижимость или бизнес: можно купить"),
                    ("stock_price", "Рынок: новый курс акций"),
                    ("sell_offer", "Рынок: покупатель на объект"),
                    ("expense", "Траты: заплатить"),
                ],
                default="",
                max_length=20,
                verbose_name="тип",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="card",
            name="symbol",
            field=models.CharField(
                blank=True,
                help_text="Например, ВКУС. Для акций и курса.",
                max_length=20,
                verbose_name="тикер акций",
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="property_name",
            field=models.CharField(
                blank=True,
                help_text="Например, «Дом 3/2». Покупатель с карточки рынка ищет объект с таким же именем.",
                max_length=100,
                verbose_name="объект",
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="price",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="За одну акцию или сколько предлагает покупатель.",
                null=True,
                verbose_name="цена",
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="cost",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="стоимость"),
        ),
        migrations.AddField(
            model_name="card",
            name="down_payment",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="первый взнос"),
        ),
        migrations.AddField(
            model_name="card",
            name="mortgage",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Пусто — стоимость минус первый взнос.",
                null=True,
                verbose_name="ипотека",
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="cashflow",
            field=models.IntegerField(
                blank=True,
                help_text="Может быть отрицательным.",
                null=True,
                verbose_name="денежный поток в месяц",
            ),
        ),
        migrations.AddField(
            model_name="card",
            name="amount",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="сумма к оплате"),
        ),
        migrations.RunPython(forward, backward),
        migrations.RemoveConstraint(model_name="card", name="card_unique_title"),
        migrations.RemoveField(model_name="card", name="effect"),
        migrations.RemoveField(model_name="card", name="color"),
        migrations.RemoveField(model_name="card", name="category"),
        migrations.RenameField(model_name="card", old_name="category_ref", new_name="category"),
        migrations.AlterField(
            model_name="card",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cards",
                to="game.category",
                verbose_name="категория",
            ),
        ),
        migrations.AddConstraint(
            model_name="card",
            constraint=models.UniqueConstraint(fields=("category", "title"), name="card_unique_title"),
        ),
    ]
