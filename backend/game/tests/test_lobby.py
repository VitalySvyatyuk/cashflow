import pytest

from game import lobby
from game.models import PLAYER_COLORS, CardCategory, Game

pytestmark = pytest.mark.django_db


def test_join_assigns_seats_and_colors(game):
    a = lobby.join_game(game, "Маша")
    b = lobby.join_game(game, "Петя")
    assert (a.seat, b.seat) == (0, 1)
    assert (a.color, b.color) == (PLAYER_COLORS[0], PLAYER_COLORS[1])


def test_join_normalizes_name(game):
    assert lobby.join_game(game, "  Анна   Мария ").name == "Анна Мария"


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_join_rejects_bad_names(game, name):
    with pytest.raises(lobby.LobbyError):
        lobby.join_game(game, name)


def test_join_rejects_duplicate_name_case_insensitive(game):
    lobby.join_game(game, "Маша")
    with pytest.raises(lobby.LobbyError, match="занято"):
        lobby.join_game(game, "маша")


def test_join_rejects_when_full(host):
    game = lobby.create_game(host, max_players=2)
    lobby.join_game(game, "А")
    lobby.join_game(game, "Б")
    with pytest.raises(lobby.LobbyError, match="места"):
        lobby.join_game(game, "В")


def test_freed_seat_is_reused(game):
    lobby.join_game(game, "А")
    b = lobby.join_game(game, "Б")
    lobby.join_game(game, "В")
    lobby.remove_player(game, b)
    assert lobby.join_game(game, "Г").seat == 1


def test_create_game_validates_player_count(host):
    with pytest.raises(lobby.LobbyError):
        lobby.create_game(host, max_players=7)


def test_start_deals_professions_and_decks(game, seeded, rnd):
    players = [lobby.join_game(game, n) for n in ("А", "Б", "В")]
    game = lobby.start_game(game, rnd=rnd)

    assert game.status == Game.Status.RUNNING
    assert game.turn_number == 1
    assert game.current_player == players[0]
    professions = set()
    for player in players:
        player.refresh_from_db()
        professions.add(player.profession_id)
        assert player.cash == player.profession.savings
        assert player.liabilities.count() == len(player.profession.liabilities)
    assert len(professions) == 3
    assert {d.category for d in game.decks.all()} == set(CardCategory)
    assert list(game.events.values_list("kind", flat=True)) == [
        "game_created",
        "player_joined",
        "player_joined",
        "player_joined",
        "game_started",
    ]


def test_start_requires_players(game, seeded):
    with pytest.raises(lobby.LobbyError, match="игрок"):
        lobby.start_game(game)


def test_cannot_join_or_start_twice_after_start(game, seeded):
    lobby.join_game(game, "А")
    lobby.start_game(game)
    with pytest.raises(lobby.LobbyError, match="началась"):
        lobby.join_game(game, "Б")
    with pytest.raises(lobby.LobbyError, match="началась"):
        lobby.start_game(game)
