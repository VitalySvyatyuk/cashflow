from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response


def _check_db():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


async def _check_channel_layer():
    layer = get_channel_layer()
    channel = await layer.new_channel()
    await layer.send(channel, {"type": "health.ping"})
    await layer.receive(channel)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def health(request):
    """Проверка, что живы БД и Redis (channel layer)."""
    checks = {}
    for name, check in (("db", _check_db), ("redis", async_to_sync(_check_channel_layer))):
        try:
            check()
            checks[name] = "ok"
        except Exception as exc:
            checks[name] = f"error: {exc}"
    healthy = all(v == "ok" for v in checks.values())
    return Response(checks, status=200 if healthy else 503)
