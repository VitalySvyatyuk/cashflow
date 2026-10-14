from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PingConsumer(AsyncJsonWebsocketConsumer):
    """Отвечает pong на ping — проверка, что WebSocket работает."""

    async def receive_json(self, content):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})
