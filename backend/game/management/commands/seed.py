from django.core.management.base import BaseCommand
from django.db import transaction

from game.models import BoardCell, Card, Profession
from game.seed_data import PROFESSIONS, build_cards, build_cells


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
        for data in PROFESSIONS:
            Profession.objects.update_or_create(name=data["name"], defaults=data)
        for data in build_cards():
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
