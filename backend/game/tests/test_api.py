import pytest

from game.models import Game

pytestmark = pytest.mark.django_db


def test_host_creates_game(host_api):
    response = host_api.post("/api/games/", {"max_players": 3}, format="json")
    assert response.status_code == 201
    assert response.data["max_players"] == 3
    assert response.data["status"] == "lobby"
    assert Game.objects.filter(code=response.data["code"]).exists()


def test_anonymous_cannot_create_game(api):
    assert api.post("/api/games/", {}, format="json").status_code == 403


def test_create_game_validates_count(host_api):
    assert host_api.post("/api/games/", {"max_players": 9}, format="json").status_code == 400


def test_host_lists_own_games(host_api, game):
    response = host_api.get("/api/games/")
    assert [g["code"] for g in response.data] == [game.code]


def test_join_returns_token_once(api, game):
    response = api.post(f"/api/games/{game.code}/join/", {"name": "Маша"}, format="json")
    assert response.status_code == 201
    assert response.data["token"]

    detail = api.get(f"/api/games/{game.code.lower()}/")
    assert detail.status_code == 200
    assert [p["name"] for p in detail.data["players"]] == ["Маша"]
    assert "token" not in detail.data["players"][0]


def test_join_error_message_is_shown(api, game):
    api.post(f"/api/games/{game.code}/join/", {"name": "Маша"}, format="json")
    response = api.post(f"/api/games/{game.code}/join/", {"name": "Маша"}, format="json")
    assert response.status_code == 400
    assert response.data["detail"] == "Это имя уже занято."


def test_unknown_game_is_404(api):
    assert api.get("/api/games/NOPE00/").status_code == 404


def test_me_by_token(api, game):
    token = api.post(f"/api/games/{game.code}/join/", {"name": "Маша"}, format="json").data["token"]
    response = api.get(f"/api/games/{game.code}/me/", HTTP_X_PLAYER_TOKEN=token)
    assert response.status_code == 200
    assert response.data["name"] == "Маша"

    assert api.get(f"/api/games/{game.code}/me/").status_code in (401, 403)
    bad = api.get(
        f"/api/games/{game.code}/me/", HTTP_X_PLAYER_TOKEN="00000000-0000-0000-0000-000000000000"
    )
    assert bad.status_code in (401, 403)


def test_player_leaves_lobby(api, game):
    token = api.post(f"/api/games/{game.code}/join/", {"name": "Маша"}, format="json").data["token"]
    response = api.delete(f"/api/games/{game.code}/me/", HTTP_X_PLAYER_TOKEN=token)
    assert response.status_code == 204
    assert not game.players.exists()


def test_host_kicks_and_starts(host_api, api, game, seeded):
    api.post(f"/api/games/{game.code}/join/", {"name": "А"}, format="json")
    b = api.post(f"/api/games/{game.code}/join/", {"name": "Б"}, format="json").data

    response = host_api.delete(f"/api/games/{game.code}/players/{b['id']}/")
    assert [p["name"] for p in response.data["players"]] == ["А"]

    assert api.post(f"/api/games/{game.code}/start/").status_code == 403
    response = host_api.post(f"/api/games/{game.code}/start/")
    assert response.status_code == 200
    assert response.data["status"] == "running"
    assert response.data["players"][0]["profession"]


def test_login_flow(api, host):
    assert api.get("/api/auth/session/").data == {"user": None}
    bad = api.post("/api/auth/login/", {"username": "host", "password": "x"}, format="json")
    assert bad.status_code in (401, 403)
    response = api.post(
        "/api/auth/login/", {"username": "host", "password": "secret"}, format="json"
    )
    assert response.data == {"user": {"username": "host", "is_host": True}}
    assert api.get("/api/auth/session/").data["user"]["is_host"] is True
