from django.db import migrations

from game.seed_data import BABY_TEXT


def update_text(apps, schema_editor):
    BoardCell = apps.get_model("game", "BoardCell")
    BoardCell.objects.filter(cell_type__kind="baby").update(description=BABY_TEXT)


class Migration(migrations.Migration):
    dependencies = [("game", "0023_property_damage")]

    operations = [migrations.RunPython(update_text, migrations.RunPython.noop)]
