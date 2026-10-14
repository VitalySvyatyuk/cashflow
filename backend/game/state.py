"""Полное состояние игры, которое получают все экраны."""

from rest_framework import serializers

from game.models import Asset, Game, GameEvent, Liability, PendingAction, Player

RECENT_EVENTS = 50


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "kind", "title", "quantity", "cost", "cashflow"]


class LiabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Liability
        fields = ["id", "title", "balance", "payment", "asset_id"]


class PlayerStateSerializer(serializers.ModelSerializer):
    profession = serializers.SerializerMethodField()
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
            "assets",
            "liabilities",
        ]

    def get_profession(self, player):
        p = player.profession
        if p is None:
            return None
        return {
            "name": p.name,
            "salary": p.salary,
            "taxes": p.taxes,
            "other_expenses": p.other_expenses,
            "per_child_expense": p.per_child_expense,
        }


class PendingActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingAction
        fields = ["id", "player_id", "kind", "payload", "status", "comment", "created_at"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameEvent
        fields = ["seq", "player_id", "kind", "payload", "created_at"]


def build_state(game_id):
    game = Game.objects.get(pk=game_id)
    players = game.players.select_related("profession").prefetch_related("assets", "liabilities")
    pending = game.pending_actions.filter(status=PendingAction.Status.PENDING)
    events = reversed(game.events.order_by("-seq")[:RECENT_EVENTS])
    return {
        "code": game.code,
        "status": game.status,
        "max_players": game.max_players,
        "turn_number": game.turn_number,
        "current_player_id": game.current_player_id,
        "players": PlayerStateSerializer(players, many=True).data,
        "pending_actions": PendingActionSerializer(pending, many=True).data,
        "events": EventSerializer(events, many=True).data,
    }


def serialize_event(event):
    return EventSerializer(event).data
