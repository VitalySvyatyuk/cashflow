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


async def connect(path, headers=()):
    communicator = WebsocketCommunicator(application, path, headers=[ORIGIN, *headers])
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
