from django.core.management.base import BaseCommand
from django.db import transaction

from game.models import BoardCell, Card, Category, Profession
from game.seed_data import (
    PROFESSIONS,
    RENAMED_PROFESSIONS,
    build_cards,
    build_categories,
    build_cells,
)


class Command(BaseCommand):
    help = "Заполняет БД профессиями, карточками и клетками поля (повторный запуск безопасен)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Сначала удалить все карточки и клетки поля (например, после правки seed_data).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            Card.objects.all().delete()
            BoardCell.objects.all().delete()
        for old, new in RENAMED_PROFESSIONS.items():
            if not Profession.objects.filter(name=new).exists():
                Profession.objects.filter(name=old).update(name=new)
        for data in PROFESSIONS:
            Profession.objects.update_or_create(name=data["name"], defaults=data)
        # Категории не перезаписываем: название и цвет могли поменять в админке.
        categories = {
            data["deck"]: Category.objects.get_or_create(deck=data["deck"], defaults=data)[0]
            for data in build_categories()
        }
        for data in build_cards():
            data["category"] = categories[data["category"]]
            Card.objects.update_or_create(
                category=data["category"], title=data["title"], defaults=data
            )
        for data in build_cells():
            BoardCell.objects.update_or_create(
                track=data["track"], position=data["position"], defaults=data
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Профессий: {Profession.objects.count()}, "
                f"карточек: {Card.objects.count()}, "
                f"клеток: {BoardCell.objects.count()}"
            )
        )
