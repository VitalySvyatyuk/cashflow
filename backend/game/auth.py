import uuid

from rest_framework.permissions import BasePermission

from game.models import Player

PLAYER_TOKEN_HEADER = "X-Player-Token"


def get_player(request, game):
    """Игрок этой игры по заголовку X-Player-Token или None."""
    raw = request.headers.get(PLAYER_TOKEN_HEADER, "")
    try:
        token = uuid.UUID(raw)
    except ValueError:
        return None
    return Player.objects.filter(game=game, token=token).first()


class IsHost(BasePermission):
    message = "Только ведущий может это сделать."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
