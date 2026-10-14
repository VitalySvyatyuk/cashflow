"""Полное состояние игры, которое получают все экраны."""

from rest_framework import serializers

from game.finance import statement
from game.models import Asset, BoardCell, Card, Game, GameEvent, Liability, PendingAction, Player

RECENT_EVENTS = 50


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "kind", "title", "key", "quantity", "cost", "cashflow"]


class LiabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Liability
        fields = ["id", "title", "balance", "payment", "asset_id"]


class PlayerStateSerializer(serializers.ModelSerializer):
    profession = serializers.SerializerMethodField()
    statement = serializers.SerializerMethodField()
    assets = AssetSerializer(many=True, read_only=True)
    liabilities = LiabilitySerializer(many=True, read_only=True)

    class Meta:
        model = Player
        fields = [
            "id",
            "name",
            "seat",
            "color",
            "profession",
            "track",
            "position",
            "cash",
            "children",
            "charity_turns",
            "skip_turns",
            "fast_track_income",
            "statement",
            "assets",
            "liabilities",
        ]

    def get_statement(self, player):
        return statement(player).as_dict()

    def get_profession(self, player):
        p = player.profession
        if p is None:
            return None
        return {
            "name": p.name,
            "emoji": p.emoji,
            "icon": p.icon.url if p.icon else None,
            "salary": p.salary,
            "taxes": p.taxes,
            "other_expenses": p.other_expenses,
            "per_child_expense": p.per_child_expense,
        }


class PendingActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingAction
        fields = ["id", "player_id", "kind", "payload", "description", "status", "created_at"]


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ["id", "category", "color", "title", "text", "effect"]


class CellSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardCell
        fields = ["id", "track", "position", "kind", "color", "title", "description", "effect"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameEvent
        fields = ["seq", "player_id", "kind", "payload", "created_at"]


def build_state(game_id):
    game = Game.objects.select_related("current_card").get(pk=game_id)
    players = game.players.select_related("profession").prefetch_related("assets", "liabilities")
    pending = game.pending_actions.filter(status=PendingAction.Status.PENDING)
    events = reversed(game.events.order_by("-seq")[:RECENT_EVENTS])
    return {
        "code": game.code,
        "status": game.status,
        "max_players": game.max_players,
        "turn_number": game.turn_number,
        "current_player_id": game.current_player_id,
        "phase": game.phase,
        "dice": game.dice,
        "current_card": CardSerializer(game.current_card).data if game.current_card else None,
        "winner_id": game.winner_id,
        "players": PlayerStateSerializer(players, many=True).data,
        "pending_actions": PendingActionSerializer(pending, many=True).data,
        "events": EventSerializer(events, many=True).data,
    }


def serialize_event(event):
    return EventSerializer(event).data


def build_board():
    return CellSerializer(BoardCell.objects.order_by("track", "position"), many=True).data
