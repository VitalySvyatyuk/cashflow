import pytest
from django.core.management import call_command
from django.db import IntegrityError

from game.models import (
    GAME_CODE_ALPHABET,
    GAME_CODE_LENGTH,
    BoardCell,
    Card,
    CardCategory,
    Game,
    Player,
    Profession,
    Track,
)
from game.seed_data import build_cards, build_cells

pytestmark = pytest.mark.django_db


def test_game_gets_readable_code(host):
    game = Game.objects.create(host=host)
    assert len(game.code) == GAME_CODE_LENGTH
    assert set(game.code) <= set(GAME_CODE_ALPHABET)


def test_game_max_players_limited(host):
    with pytest.raises(IntegrityError):
        Game.objects.create(host=host, max_players=7)


def test_player_names_unique_within_game(host):
    game = Game.objects.create(host=host)
    Player.objects.create(game=game, name="Маша", seat=0, color="#000000")
    with pytest.raises(IntegrityError):
        Player.objects.create(game=game, name="Маша", seat=1, color="#000000")


def test_player_tokens_are_unique(host):
    game = Game.objects.create(host=host)
    a = Player.objects.create(game=game, name="А", seat=0, color="#000000")
    b = Player.objects.create(game=game, name="Б", seat=1, color="#000000")
    assert a.token != b.token


def test_seed_is_idempotent():
    call_command("seed", stdout=None)
    counts = (Profession.objects.count(), Card.objects.count(), BoardCell.objects.count())
    call_command("seed", stdout=None)
    assert counts == (
        Profession.objects.count(),
        Card.objects.count(),
        BoardCell.objects.count(),
    )
    assert counts[1] == len(build_cards())


def test_seed_reset_removes_stale_cards():
    call_command("seed", stdout=None)
    Card.objects.create(category=CardCategory.DOODAD, color="#000000", title="Устаревшая")
    call_command("seed", reset=True, stdout=None)
    assert not Card.objects.filter(title="Устаревшая").exists()
    assert Card.objects.count() == len(build_cards())


def test_seed_cards_cover_all_categories():
    categories = {card["category"] for card in build_cards()}
    assert categories == set(CardCategory)


def test_seed_board_tracks_are_contiguous():
    cells = build_cells()
    for track, size in ((Track.RAT_RACE, 24), (Track.FAST_TRACK, 40)):
        positions = sorted(c["position"] for c in cells if c["track"] == track)
        assert positions == list(range(size))


def test_seed_is_deterministic():
    assert build_cards() == build_cards()
    assert build_cells() == build_cells()


def test_card_colors_are_hex():
    call_command("seed", stdout=None)
    for color in Card.objects.values_list("color", flat=True):
        assert len(color) == 7 and color.startswith("#")
