import uuid
from collections import Counter, defaultdict
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from game import engine
from game.errors import GameError
from game.events import group_name
from game.models import Game, Player
from game.state import build_state

# Коды закрытия соединения, по ним фронтенд понимает, что случилось.
CLOSE_GAME_NOT_FOUND = 4404
CLOSE_FORBIDDEN = 4403
CLOSE_REMOVED = 4410

HOST = "host"

# Кто сейчас на связи: игра → {id игрока или "host": число открытых вкладок}.
# Хранится в памяти процесса: игру обслуживает один процесс Daphne, а после
# его перезапуска все клиенты переподключаются, и счётчики собираются заново.
PRESENCE: defaultdict[int, Counter] = defaultdict(Counter)


def presence(game_id):
    online = PRESENCE[game_id]
    return {
        "type": "presence",
        "players": sorted(k for k, n in online.items() if k != HOST and n > 0),
        "host": online[HOST] > 0,
    }


class GameConsumer(AsyncJsonWebsocketConsumer):
    """Один WebSocket на экран: ведущий (по сессии) или игрок (по ?token=)."""

    async def connect(self):
        code = self.scope["url_route"]["kwargs"]["code"]
        token = parse_qs(self.scope["query_string"].decode()).get("token", [None])[0]
        identity = await self._identify(code, self.scope["user"], token)
        # Соединение принимаем всегда, чтобы клиент получил осмысленный код закрытия.
        await self.accept()
        if isinstance(identity, int):
            await self.close(code=identity)
            return

        self.game_id, self.role, self.player_id, game_code = identity
        self.group = group_name(game_code)
        await self.channel_layer.group_add(self.group, self.channel_name)
        PRESENCE[self.game_id][self._presence_key] += 1
        await self.send_json(
            {
                "type": "hello",
                "role": self.role,
                "player_id": self.player_id,
                "state": await self._state(),
                "presence": presence(self.game_id),
            }
        )
        await self._broadcast_presence()

    async def disconnect(self, code):
        if not hasattr(self, "group"):
            return
        online = PRESENCE[self.game_id]
        online[self._presence_key] -= 1
        if online[self._presence_key] <= 0:
            del online[self._presence_key]
        await self._broadcast_presence()
        await self.channel_layer.group_discard(self.group, self.channel_name)

    @property
    def _presence_key(self):
        return self.player_id if self.role == "player" else HOST

    async def _broadcast_presence(self):
        await self.channel_layer.group_send(
            self.group, {"type": "game.presence", "presence": presence(self.game_id)}
        )

    async def game_presence(self, message):
        await self.send_json(message["presence"])

    async def receive_json(self, content):
        kind = content.get("type")
        if kind == "ping":
            await self.send_json({"type": "pong"})
        elif kind == "sync":
            await self.send_json({"type": "state", "state": await self._state()})
        elif kind in ("action", "decide", "cancel"):
            try:
                await self._command(kind, content)
            except GameError as exc:
                await self.send_json({"type": "error", "message": str(exc)})
        else:
            await self.send_json({"type": "error", "message": "Неизвестная команда."})

    async def game_message(self, message):
        """Событие из группы игры (см. game.events.broadcast)."""
        payload = message["message"]
        await self.send_json(payload)
        event = payload["event"]
        if (
            self.role == "player"
            and event["kind"] == "player_left"
            and event["payload"].get("player_id") == self.player_id
        ):
            await self.close(code=CLOSE_REMOVED)

    @database_sync_to_async
    def _identify(self, code, user, token):
        game = Game.objects.by_code(code)
        if game is None:
            return CLOSE_GAME_NOT_FOUND
        if token:
            player = Player.objects.filter(game=game, token=_uuid_or_none(token)).first()
            if player is not None:
                return game.id, "player", player.id, game.code
            return CLOSE_FORBIDDEN
        if user.is_authenticated and user.is_superuser:
            return game.id, "host", None, game.code
        return CLOSE_FORBIDDEN

    @database_sync_to_async
    def _command(self, kind, content):
        """Результат придёт всем через рассылку событий; сюда — только ошибки."""
        game = Game.objects.get(pk=self.game_id)
        player = Player.objects.filter(pk=self.player_id).first() if self.player_id else None
        if self.role == "player" and player is None:
            raise GameError("Вас нет в этой игре.")
        params = content.get("params") or {}
        if not isinstance(params, dict):
            raise GameError("Неверные параметры.")

        if kind == "action":
            engine.submit_action(game, engine.Actor(player), str(content.get("kind")), params)
        elif kind == "cancel":
            if player is None:
                raise GameError("Отзывать заявки может только игрок.")
            engine.cancel_request(game, player, engine.parse_int(content.get("id"), "id"))
        else:
            if self.role != "host":
                raise GameError("Это может сделать только ведущий.")
            engine.decide(
                game,
                engine.parse_int(content.get("id"), "id"),
                bool(content.get("approve")),
                params,
                str(content.get("comment", "")),
            )

    @database_sync_to_async
    def _state(self):
        return build_state(self.game_id)


def _uuid_or_none(value):
    try:
        return uuid.UUID(value)
    except ValueError:
        return None
