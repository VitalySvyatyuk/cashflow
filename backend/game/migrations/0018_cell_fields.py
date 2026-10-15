"""Клетки: эффект разбит на поля; у типа клетки нет отдельного названия — это сам тип."""

import django.core.validators
from django.db import migrations, models


def forward(apps, schema_editor):
    BoardCell = apps.get_model("game", "BoardCell")
    for cell in BoardCell.objects.all():
        effect = cell.effect or {}
        cell.cost = effect.get("cost")
        cell.cashflow = effect.get("cashflow")
        if "cash_share" in effect:
            cell.loss_percent = round(effect["cash_share"] * 100)
        cell.save(update_fields=["cost", "cashflow", "loss_percent"])


def backward(apps, schema_editor):
    BoardCell = apps.get_model("game", "BoardCell")
    for cell in BoardCell.objects.all():
        effect = {}
        if cell.cost is not None:
            effect["cost"] = cell.cost
        if cell.cashflow is not None:
            effect["cashflow"] = cell.cashflow
        if cell.loss_percent is not None:
            effect["cash_share"] = cell.loss_percent / 100
        cell.effect = effect
        cell.save(update_fields=["effect"])


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0017_cell_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="boardcell",
            name="cost",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Бизнес, мечта, благотворительность в большом круге.",
                null=True,
                verbose_name="стоимость",
            ),
        ),
        migrations.AddField(
            model_name="boardcell",
            name="cashflow",
            field=models.IntegerField(
                blank=True,
                help_text="Бизнес: прибавка к доходу в День денежного потока.",
                null=True,
                verbose_name="денежный поток в месяц",
            ),
        ),
        migrations.AddField(
            model_name="boardcell",
            name="loss_percent",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Клетка «Потеря»: какую часть наличных теряет игрок.",
                null=True,
                validators=[django.core.validators.MaxValueValidator(100)],
                verbose_name="потеря, % наличных",
            ),
        ),
        migrations.RunPython(forward, backward),
        migrations.RemoveField(model_name="boardcell", name="effect"),
        migrations.RemoveField(model_name="celltype", name="name"),
        migrations.AlterField(
            model_name="celltype",
            name="kind",
            field=models.CharField(
                choices=[
                    ("opportunity", "Возможность"),
                    ("market", "Рынок"),
                    ("doodad", "Траты"),
                    ("paycheck", "Доход"),
                    ("charity", "Благотворительность"),
                    ("baby", "Ребёнок"),
                    ("downsized", "Увольнение"),
                    ("cashflow_day", "День денежного потока"),
                    ("business", "Бизнес"),
                    ("dream", "Мечта"),
                    ("loss", "Потеря"),
                ],
                max_length=20,
                unique=True,
                verbose_name="тип",
            ),
        ),
    ]
