import pytest
from channels.testing import WebsocketCommunicator

from config.asgi import application


@pytest.mark.django_db
def test_health_ok(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"db": "ok", "redis": "ok"}


@pytest.mark.asyncio
async def test_ws_ping():
    communicator = WebsocketCommunicator(
        application, "/ws/ping/", headers=[(b"origin", b"http://localhost")]
    )
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"type": "ping"})
    assert await communicator.receive_json_from() == {"type": "pong"}
    await communicator.disconnect()
