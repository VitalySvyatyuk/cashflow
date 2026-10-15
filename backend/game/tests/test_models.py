import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction

from game.models import (
    GAME_CODE_ALPHABET,
    GAME_CODE_LENGTH,
    BoardCell,
    Card,
    CardCategory,
    CardKind,
    Category,
    CellKind,
    CellType,
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
    Card.objects.create(
        category=Category.objects.get(deck=CardCategory.DOODAD),
        kind=CardKind.EXPENSE,
        title="Устаревшая",
        amount=1,
    )
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


def test_seed_creates_categories_once():
    call_command("seed", stdout=None)
    assert set(Category.objects.values_list("deck", flat=True)) == set(CardCategory)
    small = Category.objects.get(deck=CardCategory.SMALL_DEAL)
    small.name, small.color = "Мелочь", "#123456"
    small.save()
    call_command("seed", stdout=None)  # название и цвет из админки не затираются
    small.refresh_from_db()
    assert (small.name, small.color) == ("Мелочь", "#123456")
    assert Card.objects.filter(category=small).first().color == "#123456"


def test_cell_color_comes_from_its_type():
    call_command("seed", stdout=None)
    business = CellType.objects.get(kind=CellKind.BUSINESS)
    business.name, business.color = "Своё дело", "#abcdef"
    business.save()
    call_command("seed", stdout=None)  # не затирает правки из админки
    cells = BoardCell.objects.filter(cell_type__kind=CellKind.BUSINESS)
    assert cells.count() > 1
    assert {c.color for c in cells} == {"#abcdef"}
    assert {c.cell_type.name for c in cells} == {"Своё дело"}


def test_card_effect_from_fields():
    call_command("seed", stdout=None)
    card = Card(
        category=Category.objects.get(deck=CardCategory.BIG_DEAL),
        kind=CardKind.REAL_ESTATE,
        title="Дом",
        property_name="Дом",
        cost=100,
        down_payment=20,
        cashflow=5,
    )
    card.save()
    assert card.effect == {
        "type": "real_estate",
        "property": "Дом",
        "cost": 100,
        "down_payment": 20,
        "cashflow": 5,
        "mortgage": 80,  # посчитана сама
    }


def test_card_validation_by_kind():
    call_command("seed", stdout=None)
    card = Card(
        category=Category.objects.get(deck=CardCategory.MARKET),
        kind=CardKind.STOCK,
        title="Акции",
        symbol="ТСТ",
    )
    with pytest.raises(ValidationError) as error:
        card.full_clean()
    assert set(error.value.message_dict) >= {"kind", "price"}


def test_game_code_is_four_digits(host):
    code = Game.objects.create(host=host).code
    assert len(code) == 4 and code.isdigit()


def test_code_unique_only_among_active_games(host):
    Game.objects.create(host=host, code="1234", status=Game.Status.FINISHED)
    active = Game.objects.create(host=host, code="1234")
    with pytest.raises(IntegrityError), transaction.atomic():
        Game.objects.create(host=host, code="1234")
    assert Game.objects.by_code(" 1234 ") == active


def test_new_code_avoids_active_games(host, monkeypatch):
    Game.objects.create(host=host, code="1111")
    codes = iter(["1111", "2222"])
    monkeypatch.setattr("game.models.generate_game_code", lambda: next(codes))
    assert Game.objects.create(host=host).code == "2222"


def test_profession_icon_rejects_svg():
    from django.core.exceptions import ValidationError
    from django.core.files.uploadedfile import SimpleUploadedFile

    profession = Profession(
        name="Тест", salary=1, taxes=0, other_expenses=0, per_child_expense=0, savings=0
    )
    profession.icon = SimpleUploadedFile("x.svg", b"<svg onload='alert(1)'/>")
    with pytest.raises(ValidationError):
        profession.full_clean()


def test_state_includes_profession_icon(host, seeded):
    from game import lobby
    from game.state import build_state

    game = lobby.create_game(host, 1)
    lobby.join_game(game, "Маша")
    lobby.start_game(game)
    profession = build_state(game.id)["players"][0]["profession"]
    assert profession["emoji"]
    assert profession["icon"] is None
