"""Клетки поля: тип — отдельная таблица (название, цвет), цвет у клетки убран."""

import django.db.models.deletion
from django.db import migrations, models

KINDS = [
    ("opportunity", "Возможность", "#2e7d32"),
    ("market", "Рынок", "#1565c0"),
    ("doodad", "Траты", "#d81b60"),
    ("paycheck", "Доход", "#f9a825"),
    ("charity", "Благотворительность", "#ef6c00"),
    ("baby", "Ребёнок", "#8e24aa"),
    ("downsized", "Увольнение", "#424242"),
    ("cashflow_day", "День денежного потока", "#fbc02d"),
    ("business", "Бизнес", "#00897b"),
    ("dream", "Мечта", "#5e35b1"),
    ("loss", "Потеря", "#c62828"),
]


def forward(apps, schema_editor):
    BoardCell = apps.get_model("game", "BoardCell")
    CellType = apps.get_model("game", "CellType")
    types = {}
    for kind, name, default in KINDS:
        # Цвет — тот, что уже был у клеток этого типа.
        first = BoardCell.objects.filter(kind=kind).exclude(color="").first()
        types[kind] = CellType.objects.create(
            kind=kind, name=name, color=first.color if first else default
        )
    for cell in BoardCell.objects.all():
        cell.cell_type = types[cell.kind]
        cell.save(update_fields=["cell_type"])


def backward(apps, schema_editor):
    BoardCell = apps.get_model("game", "BoardCell")
    for cell in BoardCell.objects.select_related("cell_type"):
        cell.kind = cell.cell_type.kind
        cell.color = cell.cell_type.color
        cell.save(update_fields=["kind", "color"])


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0016_card_category_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="CellType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[(kind, name) for kind, name, _ in KINDS],
                        max_length=20,
                        unique=True,
                        verbose_name="код",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="название")),
                ("color", models.CharField(default="#757575", max_length=7, verbose_name="цвет")),
            ],
            options={
                "verbose_name": "тип клетки",
                "verbose_name_plural": "типы клеток",
                "ordering": ["id"],
            },
        ),
        migrations.AddField(
            model_name="boardcell",
            name="cell_type",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to="game.celltype"
            ),
        ),
        migrations.RunPython(forward, backward),
        migrations.RemoveField(model_name="boardcell", name="kind"),
        migrations.RemoveField(model_name="boardcell", name="color"),
        migrations.AlterField(
            model_name="boardcell",
            name="cell_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cells",
                to="game.celltype",
                verbose_name="тип",
            ),
        ),
    ]
