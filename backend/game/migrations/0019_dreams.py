"""Мечты: у игрока — выбранная клетка-мечта; в большом круге одна благотворительность,
остальные три клетки стали мечтами, у каждой из 11 мечт — своё название и цена."""

import django.db.models.deletion
from django.db import migrations, models

from game.seed_data import DREAMS, FAST_TRACK_CHARITY_POSITION, FAST_TRACK_PATTERN


def forward(apps, schema_editor):
    BoardCell = apps.get_model("game", "BoardCell")
    CellType = apps.get_model("game", "CellType")
    dream_type, _ = CellType.objects.get_or_create(kind="dream", defaults={"color": "#5e35b1"})
    cells = {c.position: c for c in BoardCell.objects.filter(track="fast_track")}
    if not cells:
        return  # пустая БД — поле создаст seed
    dreams = iter(DREAMS)
    for position, kind in enumerate(FAST_TRACK_PATTERN):
        if kind != "dream" or position not in cells:
            continue
        title, description, cost = next(dreams)
        cell = cells[position]
        cell.cell_type = dream_type
        cell.title = title
        cell.description = description
        cell.cost = cost
        cell.cashflow = None
        cell.loss_percent = None
        cell.save()
    assert cells[FAST_TRACK_CHARITY_POSITION].cell_type.kind == "charity"


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0018_cell_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="dream",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"cell_type__kind": "dream"},
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="dreamers",
                to="game.boardcell",
                verbose_name="мечта",
            ),
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
