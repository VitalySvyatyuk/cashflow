from channels_redis.core import RedisChannelLayer
from django.conf import settings


def test_redis_read_timeout_exceeds_blocking_wait():
    """Иначе соединение рвётся, если 5 секунд никто ничего не делает."""
    [host] = settings.CHANNEL_LAYERS["default"]["CONFIG"]["hosts"]
    assert host["socket_timeout"] > RedisChannelLayer.brpop_timeout
