"""Лобби: создание игры, вход игроков, старт."""

import random

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from game.models import (
    MAX_PLAYERS,
    PLAYER_COLORS,
    Card,
    CardCategory,
    DeckState,
    Game,
    GameEvent,
    Liability,
    Player,
    Profession,
)

MAX_NAME_LENGTH = 40


class LobbyError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


def log_event(game, kind, player=None, **payload):
    """Пишет событие в журнал. Вызывать внутри транзакции с заблокированной игрой."""
    last = game.events.aggregate(last=Max("seq"))["last"] or 0
    return GameEvent.objects.create(
        game=game, seq=last + 1, player=player, kind=kind, payload=payload
    )


def _lock(game):
    return Game.objects.select_for_update().get(pk=game.pk)


def create_game(host, max_players):
    if not 1 <= max_players <= MAX_PLAYERS:
        raise LobbyError(f"Игроков может быть от 1 до {MAX_PLAYERS}.")
    with transaction.atomic():
        game = Game.objects.create(host=host, max_players=max_players)
        log_event(game, "game_created", max_players=max_players)
    return game


def join_game(game, name):
    name = " ".join(name.split())
    if not name:
        raise LobbyError("Введите имя.")
    if len(name) > MAX_NAME_LENGTH:
        raise LobbyError(f"Имя длиннее {MAX_NAME_LENGTH} символов.")

    with transaction.atomic():
        game = _lock(game)
        if game.status != Game.Status.LOBBY:
            raise LobbyError("Игра уже началась.")
        players = list(game.players.all())
        if len(players) >= game.max_players:
            raise LobbyError("Все места заняты.")
        if any(p.name.casefold() == name.casefold() for p in players):
            raise LobbyError("Это имя уже занято.")

        taken = {p.seat for p in players}
        seat = min(s for s in range(MAX_PLAYERS) if s not in taken)
        player = Player.objects.create(game=game, name=name, seat=seat, color=PLAYER_COLORS[seat])
        log_event(game, "player_joined", player=player, name=name)
    return player


def remove_player(game, player):
    """Ведущий убирает игрока из лобби (или игрок выходит сам)."""
    with transaction.atomic():
        game = _lock(game)
        if game.status != Game.Status.LOBBY:
            raise LobbyError("После старта игроков убрать нельзя.")
        log_event(game, "player_left", name=player.name)
        player.delete()


def start_game(game, rnd=random):
    with transaction.atomic():
        game = _lock(game)
        if game.status != Game.Status.LOBBY:
            raise LobbyError("Игра уже началась.")
        players = list(game.players.order_by("seat"))
        if not players:
            raise LobbyError("Нет ни одного игрока.")
        professions = list(Profession.objects.all())
        if not professions:
            raise LobbyError("Нет профессий — выполните make seed.")

        # Разные профессии, пока их хватает.
        rnd.shuffle(professions)
        for i, player in enumerate(players):
            _deal_profession(player, professions[i % len(professions)])

        for category in CardCategory:
            ids = list(
                Card.objects.filter(category=category, is_active=True).values_list("id", flat=True)
            )
            rnd.shuffle(ids)
            DeckState.objects.create(game=game, category=category, card_ids=ids)

        game.status = Game.Status.RUNNING
        game.started_at = timezone.now()
        game.turn_number = 1
        game.current_player = players[0]
        game.save()
        log_event(
            game,
            "game_started",
            professions={p.name: p.profession.name for p in players},
        )
    return game


def _deal_profession(player, profession):
    player.profession = profession
    player.cash = profession.savings
    player.save()
    Liability.objects.bulk_create(
        Liability(
            player=player,
            title=item["title"],
            balance=item["balance"],
            payment=item["payment"],
        )
        for item in profession.liabilities
    )
