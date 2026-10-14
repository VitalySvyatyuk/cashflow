from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from game import lobby
from game.auth import IsHost, get_player
from game.models import Game
from game.serializers import (
    CreateGameSerializer,
    GameSerializer,
    JoinedPlayerSerializer,
    JoinSerializer,
    OwnPlayerSerializer,
)
from game.state import build_board


def _game(code):
    game = Game.objects.by_code(code)
    if game is None:
        raise Http404("Игра не найдена.")
    return game


def _game_response(game, status_code=status.HTTP_200_OK):
    game = Game.objects.prefetch_related("players").get(pk=game.pk)
    return Response(GameSerializer(game).data, status=status_code)


def _run(action, *args):
    try:
        return action(*args)
    except lobby.LobbyError as exc:
        raise ValidationError({"detail": str(exc)}) from exc


@api_view(["GET", "POST"])
@permission_classes([IsHost])
def games(request):
    if request.method == "GET":
        qs = Game.objects.filter(host=request.user).prefetch_related("players")
        return Response(GameSerializer(qs, many=True).data)
    data = CreateGameSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    game = _run(lobby.create_game, request.user, data.validated_data["max_players"])
    return _game_response(game, status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def game_detail(request, code):
    return Response(GameSerializer(_game(code)).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def join(request, code):
    game = _game(code)
    data = JoinSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    player = _run(lobby.join_game, game, data.validated_data["name"])
    return Response(JoinedPlayerSerializer(player).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "DELETE"])
@permission_classes([AllowAny])
def me(request, code):
    """Игрок по токену: проверить, что он ещё в игре, или выйти из лобби."""
    game = _game(code)
    player = get_player(request, game)
    if player is None:
        raise NotAuthenticated("Игрок не найден — войдите в игру заново.")
    if request.method == "DELETE":
        _run(lobby.remove_player, game, player)
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(OwnPlayerSerializer(player).data)


@api_view(["DELETE"])
@permission_classes([IsHost])
def kick(request, code, player_id):
    game = _game(code)
    player = get_object_or_404(game.players, pk=player_id)
    _run(lobby.remove_player, game, player)
    return _game_response(game)


@api_view(["POST"])
@permission_classes([IsHost])
def start(request, code):
    game = _run(lobby.start_game, _game(code))
    return _game_response(game)


@api_view(["GET"])
@permission_classes([AllowAny])
def board(request):
    """Клетки поля: обе дорожки по порядку."""
    return Response(build_board())
