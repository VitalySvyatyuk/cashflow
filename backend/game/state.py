"""Полное состояние игры, которое получают все экраны."""

from rest_framework import serializers

from game.finance import statement
from game.models import (
    Asset,
    BoardCell,
    Card,
    Game,
    GameEvent,
    Liability,
    LoanOffer,
    PendingAction,
    Player,
)

RECENT_EVENTS = 50


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "kind", "title", "description", "key", "quantity", "cost", "cashflow"]


class LiabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Liability
        fields = ["id", "title", "balance", "payment", "asset_id", "lender_id", "rate"]


class LoanGivenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Liability
        fields = ["id", "player_id", "balance", "payment", "rate"]


class LoanOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanOffer
        fields = ["id", "lender_id", "borrower_id", "amount", "rate"]


class PlayerStateSerializer(serializers.ModelSerializer):
    profession = serializers.SerializerMethodField()
    statement = serializers.SerializerMethodField()
    dice_options = serializers.SerializerMethodField()
    assets = AssetSerializer(many=True, read_only=True)
    liabilities = LiabilitySerializer(many=True, read_only=True)
    loans_given = LoanGivenSerializer(many=True, read_only=True)

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
            "fast_track_charity",
            "dice_options",
            "statement",
            "assets",
            "liabilities",
            "loans_given",
        ]

    def get_dice_options(self, player):
        return player.dice_options()

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
    # Экран знает колоду по коду; цвет и название — из категории.
    category = serializers.CharField(source="category.deck")
    category_name = serializers.CharField(source="category.name")
    color = serializers.CharField(source="category.color")
    effect = serializers.DictField(read_only=True)

    class Meta:
        model = Card
        fields = ["id", "category", "category_name", "color", "title", "text", "effect"]


class CellSerializer(serializers.ModelSerializer):
    # Код, название и цвет — из типа клетки (меняются в админке для всех клеток сразу).
    kind = serializers.CharField(source="cell_type.kind")
    kind_name = serializers.CharField(source="cell_type.name")
    color = serializers.CharField(source="cell_type.color")

    class Meta:
        model = BoardCell
        fields = [
            "id",
            "track",
            "position",
            "kind",
            "kind_name",
            "color",
            "title",
            "description",
            "effect",
        ]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameEvent
        fields = ["seq", "player_id", "kind", "payload", "created_at"]


def build_state(game_id):
    game = Game.objects.select_related("current_card__category").get(pk=game_id)
    players = game.players.select_related("profession").prefetch_related(
        "assets", "liabilities", "loans_given"
    )
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
        "paydays": game.paydays,
        "offer_player_id": game.offer_player_id,
        "stock_waiting": game.stock_waiting,
        "loan_offers": LoanOfferSerializer(game.loan_offers.all(), many=True).data,
        "current_card": CardSerializer(game.current_card).data if game.current_card else None,
        "winner_id": game.winner_id,
        "players": PlayerStateSerializer(players, many=True).data,
        "pending_actions": PendingActionSerializer(pending, many=True).data,
        "events": EventSerializer(events, many=True).data,
    }


def serialize_event(event):
    return EventSerializer(event).data


def build_board():
    cells = BoardCell.objects.select_related("cell_type").order_by("track", "position")
    return CellSerializer(cells, many=True).data
