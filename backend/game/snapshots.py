"""Снимки изменяемого состояния игры для отмены последнего действия."""

from django.forms.models import model_to_dict

from game.models import Asset, DeckState, GameSnapshot, Liability, Player

KEEP_SNAPSHOTS = 30

GAME_FIELDS = [
    "turn_number",
    "phase",
    "dice",
    "current_card_id",
    "current_player_id",
    "winner_id",
    "paydays",
]
PLAYER_FIELDS = [
    "track",
    "position",
    "cash",
    "children",
    "charity_turns",
    "skip_turns",
    "fast_track_income",
]


def _row(obj):
    return model_to_dict(obj) | {"id": obj.id}


def _fk_ids(row, *fks):
    """model_to_dict отдаёт FK как player=5 — превращаем в player_id=5."""
    return {(k + "_id" if k in fks else k): v for k, v in row.items()}


def capture(game, label):
    players = list(game.players.all())
    data = {
        "game": {f: getattr(game, f) for f in GAME_FIELDS} | {"status": game.status},
        "players": [{"id": p.id} | {f: getattr(p, f) for f in PLAYER_FIELDS} for p in players],
        "assets": [_row(a) for a in Asset.objects.filter(player__game=game)],
        "liabilities": [_row(li) for li in Liability.objects.filter(player__game=game)],
        "decks": [
            {"id": d.id, "card_ids": d.card_ids, "next_index": d.next_index}
            for d in game.decks.all()
        ],
    }
    GameSnapshot.objects.create(game=game, label=label, data=data)
    stale = game.snapshots.values_list("id", flat=True)[KEEP_SNAPSHOTS:]
    GameSnapshot.objects.filter(id__in=list(stale)).delete()


def restore_latest(game):
    """Возвращает игру к последнему снимку и удаляет его. None — если отменять нечего."""
    snapshot = game.snapshots.first()
    if snapshot is None:
        return None
    data = snapshot.data

    for field in GAME_FIELDS:
        setattr(game, field, data["game"][field])
    # Пауза — решение ведущего, отмена её не снимает. А вот победу отменить можно.
    if game.status == game.Status.FINISHED:
        game.status = data["game"]["status"]
        game.finished_at = None
    game.save()

    for row in data["players"]:
        Player.objects.filter(id=row["id"], game=game).update(**{f: row[f] for f in PLAYER_FIELDS})

    Liability.objects.filter(player__game=game).delete()
    Asset.objects.filter(player__game=game).delete()
    Asset.objects.bulk_create(
        Asset(**_fk_ids(row, "player", "source_card")) for row in data["assets"]
    )
    Liability.objects.bulk_create(
        Liability(**_fk_ids(row, "player", "asset")) for row in data["liabilities"]
    )
    for row in data["decks"]:
        DeckState.objects.filter(id=row["id"], game=game).update(
            card_ids=row["card_ids"], next_index=row["next_index"]
        )

    label = snapshot.label
    snapshot.delete()
    return label
