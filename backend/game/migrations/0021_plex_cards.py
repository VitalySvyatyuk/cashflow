from django.db import migrations

from game.seed_data import build_plex_cards


def add_cards(apps, schema_editor):
    Card = apps.get_model("game", "Card")
    Category = apps.get_model("game", "Category")
    categories = {c.deck: c for c in Category.objects.all()}
    for data in build_plex_cards():
        category = categories.get(data.pop("category"))
        if category is None:  # пустая база: карточки заведёт make seed
            return
        Card.objects.get_or_create(category=category, title=data.pop("title"), defaults=data)


class Migration(migrations.Migration):
    dependencies = [("game", "0020_card_units")]

    operations = [migrations.RunPython(add_cards, migrations.RunPython.noop)]
