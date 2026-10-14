import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test import Client

from config.asgi import application
from game import lobby
from game.consumers import CLOSE_FORBIDDEN, CLOSE_GAME_NOT_FOUND, CLOSE_REMOVED

pytestmark = [pytest.mark.asyncio, pytest.mark.django_db(transaction=True)]

ORIGIN = (b"origin", b"http://localhost")


@pytest.fixture(autouse=True)
def in_memory_layer(settings):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


class GameClient(WebsocketCommunicator):
    """Коммуникатор, который по умолчанию пропускает рассылки о присутствии."""

    skip_presence = True

    async def receive_json_from(self, timeout=1):
        while True:
            message = await super().receive_json_from(timeout)
            if not (self.skip_presence and message.get("type") == "presence"):
                return message

    async def next_presence(self):
        while True:
            message = await WebsocketCommunicator.receive_json_from(self, 1)
            if message.get("type") == "presence":
                return message


async def connect(path, headers=()):
    communicator = GameClient(application, path, headers=[ORIGIN, *headers])
    connected, _ = await communicator.connect()
    assert connected
    return communicator


async def host_cookie(host):
    client = Client()
    await sync_to_async(client.force_login)(host)
    session = client.cookies[settings.SESSION_COOKIE_NAME].value
    return (b"cookie", f"{settings.SESSION_COOKIE_NAME}={session}".encode())


async def test_player_gets_hello_with_state(game):
    player = await sync_to_async(lobby.join_game)(game, "Маша")
    ws = await connect(f"/ws/games/{game.code}/?token={player.token}")
    hello = await ws.receive_json_from()
    assert hello["type"] == "hello"
    assert hello["role"] == "player"
    assert hello["player_id"] == player.id
    assert [p["name"] for p in hello["state"]["players"]] == ["Маша"]
    await ws.disconnect()


async def test_host_connects_by_session(game, host):
    ws = await connect(f"/ws/games/{game.code}/", headers=[await host_cookie(host)])
    hello = await ws.receive_json_from()
    assert hello["role"] == "host"
    assert hello["state"]["code"] == game.code
    await ws.disconnect()


@pytest.mark.parametrize(
    "query, code",
    [
        ("", CLOSE_FORBIDDEN),
        ("?token=not-a-uuid", CLOSE_FORBIDDEN),
        ("?token=00000000-0000-0000-0000-000000000000", CLOSE_FORBIDDEN),
    ],
)
async def test_rejects_unknown_identity(game, query, code):
    ws = await connect(f"/ws/games/{game.code}/{query}")
    assert (await ws.receive_output())["code"] == code


async def test_unknown_game(db):
    ws = await connect("/ws/games/abcd/")
    assert (await ws.receive_output())["code"] == CLOSE_GAME_NOT_FOUND


async def test_lobby_events_are_broadcast(game, host):
    ws = await connect(f"/ws/games/{game.code}/", headers=[await host_cookie(host)])
    await ws.receive_json_from()  # hello

    await sync_to_async(lobby.join_game)(game, "Петя")
    message = await ws.receive_json_from()
    assert message["type"] == "event"
    assert message["event"]["kind"] == "player_joined"
    assert [p["name"] for p in message["state"]["players"]] == ["Петя"]
    await ws.disconnect()


async def test_removed_player_is_disconnected(game):
    player = await sync_to_async(lobby.join_game)(game, "Маша")
    ws = await connect(f"/ws/games/{game.code}/?token={player.token}")
    await ws.receive_json_from()  # hello

    await sync_to_async(lobby.remove_player)(game, player)
    message = await ws.receive_json_from()
    assert message["event"]["kind"] == "player_left"
    assert message["state"]["players"] == []
    assert (await ws.receive_output())["code"] == CLOSE_REMOVED


async def test_ping_and_sync(game):
    player = await sync_to_async(lobby.join_game)(game, "Маша")
    ws = await connect(f"/ws/games/{game.code}/?token={player.token}")
    await ws.receive_json_from()
    await ws.send_json_to({"type": "ping"})
    assert await ws.receive_json_from() == {"type": "pong"}
    await ws.send_json_to({"type": "sync"})
    assert (await ws.receive_json_from())["type"] == "state"
    await ws.send_json_to({"type": "nonsense"})
    assert (await ws.receive_json_from())["type"] == "error"
    await ws.disconnect()


async def receive_until(ws, kind):
    while True:
        message = await ws.receive_json_from()
        if message.get("type") == "event" and message["event"]["kind"] == kind:
            return message


async def test_actions_over_websocket(game, host, seeded):
    masha = await sync_to_async(lobby.join_game)(game, "Маша")
    await sync_to_async(lobby.start_game)(game)
    player_ws = await connect(f"/ws/games/{game.code}/?token={masha.token}")
    host_ws = await connect(f"/ws/games/{game.code}/", headers=[await host_cookie(host)])
    await player_ws.receive_json_from()
    await host_ws.receive_json_from()

    # Ошибка приходит только отправителю
    await player_ws.send_json_to({"type": "action", "kind": "end_turn"})
    assert (await player_ws.receive_json_from()) == {
        "type": "error",
        "message": "Сейчас это сделать нельзя.",
    }

    # Заявка на кредит → ведущий видит её в состоянии → одобряет
    await player_ws.send_json_to(
        {"type": "action", "kind": "take_loan", "params": {"amount": 1000}}
    )
    requested = await receive_until(host_ws, "action_requested")
    [pending] = requested["state"]["pending_actions"]
    assert pending["description"] == "взять кредит $1 000"

    await player_ws.send_json_to({"type": "decide", "id": pending["id"], "approve": True})
    assert await receive_until(player_ws, "action_requested")  # своё же событие
    error = await player_ws.receive_json_from()
    assert error == {"type": "error", "message": "Это может сделать только ведущий."}

    await host_ws.send_json_to({"type": "decide", "id": pending["id"], "approve": True})
    taken = await receive_until(host_ws, "loan_taken")
    assert taken["state"]["pending_actions"] == []
    me = next(p for p in taken["state"]["players"] if p["id"] == masha.id)
    assert any(li["title"] == "Банковский кредит" for li in me["liabilities"])

    await player_ws.disconnect()
    await host_ws.disconnect()


async def test_host_pause_over_websocket(game, host, seeded):
    await sync_to_async(lobby.join_game)(game, "Маша")
    await sync_to_async(lobby.start_game)(game)
    host_ws = await connect(f"/ws/games/{game.code}/", headers=[await host_cookie(host)])
    await host_ws.receive_json_from()
    await host_ws.send_json_to({"type": "action", "kind": "pause"})
    paused = await receive_until(host_ws, "paused")
    assert paused["state"]["status"] == "paused"
    await host_ws.disconnect()


async def test_presence_tracks_players_and_host(game, host):
    masha = await sync_to_async(lobby.join_game)(game, "Маша")
    player_ws = await connect(f"/ws/games/{game.code}/?token={masha.token}")
    hello = await player_ws.receive_json_from()
    assert hello["presence"] == {"type": "presence", "players": [masha.id], "host": False}

    host_ws = await connect(f"/ws/games/{game.code}/", headers=[await host_cookie(host)])
    assert (await host_ws.receive_json_from())["presence"]["host"] is True
    online = {"type": "presence", "players": [masha.id], "host": True}
    assert await host_ws.next_presence() == online

    # Вторая вкладка того же игрока: закрыли одну из двух — игрок всё ещё в сети.
    second = await connect(f"/ws/games/{game.code}/?token={masha.token}")
    await second.receive_json_from()
    assert await host_ws.next_presence() == online
    await second.disconnect()
    assert await host_ws.next_presence() == online

    await player_ws.disconnect()
    assert await host_ws.next_presence() == {"type": "presence", "players": [], "host": True}
    await host_ws.disconnect()
