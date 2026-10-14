"""Журнал событий и рассылка их всем подключённым экранам."""

import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Max
from rest_framework.utils.encoders import JSONEncoder

from game.models import GameEvent
from game.state import build_state, serialize_event

logger = logging.getLogger(__name__)


def group_name(code):
    return f"game_{code}"


def log_event(game, kind, player=None, **payload):
    """Пишет событие в журнал и после коммита рассылает его вместе с новым состоянием.

    Вызывать внутри транзакции с заблокированной игрой — иначе seq может повториться.
    """
    last = game.events.aggregate(last=Max("seq"))["last"] or 0
    event = GameEvent.objects.create(
        game=game, seq=last + 1, player=player, kind=kind, payload=payload
    )
    transaction.on_commit(lambda: _safe_broadcast(event))
    return event


def _safe_broadcast(event):
    # Изменение уже в БД: если Redis недоступен, клиенты догонят состояние при переподключении.
    try:
        broadcast(event)
    except Exception:
        logger.exception("Не удалось разослать событие %s", event.pk)


def broadcast(event):
    message = {
        "type": "event",
        "event": serialize_event(event),
        "state": build_state(event.game_id),
    }
    # Даты и Decimal → JSON-совместимые типы, как в ответах API.
    message = json.loads(json.dumps(message, cls=JSONEncoder))
    async_to_sync(get_channel_layer().group_send)(
        group_name(event.game.code), {"type": "game.message", "message": message}
    )
