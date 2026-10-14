from rest_framework import serializers

from game.models import MAX_PLAYERS, Game, Liability, Player


class PublicPlayerSerializer(serializers.ModelSerializer):
    profession = serializers.CharField(source="profession.name", default=None)
    profession_emoji = serializers.CharField(source="profession.emoji", default="")

    class Meta:
        model = Player
        fields = ["id", "name", "seat", "color", "profession", "profession_emoji"]


class LiabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Liability
        fields = ["id", "title", "balance", "payment"]


class OwnPlayerSerializer(PublicPlayerSerializer):
    """То, что игрок видит о себе. Токен отдаём только при входе."""

    liabilities = LiabilitySerializer(many=True, read_only=True)

    class Meta(PublicPlayerSerializer.Meta):
        fields = PublicPlayerSerializer.Meta.fields + ["cash", "liabilities"]


class JoinedPlayerSerializer(OwnPlayerSerializer):
    class Meta(OwnPlayerSerializer.Meta):
        fields = OwnPlayerSerializer.Meta.fields + ["token"]


class GameSerializer(serializers.ModelSerializer):
    players = PublicPlayerSerializer(many=True, read_only=True)
    current_player_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Game
        fields = [
            "code",
            "status",
            "max_players",
            "turn_number",
            "current_player_id",
            "players",
            "created_at",
        ]


class CreateGameSerializer(serializers.Serializer):
    max_players = serializers.IntegerField(min_value=1, max_value=MAX_PLAYERS, default=4)


class JoinSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
