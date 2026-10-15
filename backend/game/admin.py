from django.contrib import admin
from django.utils.html import format_html

from game.models import (
    Asset,
    BoardCell,
    Card,
    DeckState,
    Game,
    GameEvent,
    Liability,
    PendingAction,
    Player,
    Profession,
)


def color_swatch(obj):
    return format_html(
        '<span style="display:inline-block;width:14px;height:14px;border-radius:3px;'
        'background:{};vertical-align:middle"></span> {}',
        obj.color,
        obj.color,
    )


color_swatch.short_description = "цвет"


@admin.display(description="иконка")
def profession_icon(obj):
    if obj.icon:
        return format_html(
            '<img src="{}" style="width:32px;height:32px;object-fit:contain">', obj.icon.url
        )
    return format_html('<span style="font-size:24px">{}</span>', obj.emoji or "—")


@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = [profession_icon, "name", "salary", "taxes", "other_expenses", "savings"]
    list_display_links = [profession_icon, "name"]
    readonly_fields = [profession_icon]
    fields = [
        "name",
        ("emoji", "icon"),
        profession_icon,
        "salary",
        "taxes",
        "other_expenses",
        "per_child_expense",
        "savings",
        "liabilities",
    ]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ["title", "category", color_swatch, "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["title", "text"]


@admin.register(BoardCell)
class BoardCellAdmin(admin.ModelAdmin):
    list_display = ["position", "track", "kind", color_swatch, "title"]
    list_filter = ["track", "kind"]


class PlayerInline(admin.TabularInline):
    model = Player
    fields = ["seat", "name", "profession", "track", "position", "cash"]
    extra = 0
    show_change_link = True


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["code", "host", "status", "max_players", "turn_number", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["code", "created_at"]
    inlines = [PlayerInline]


class AssetInline(admin.TabularInline):
    model = Asset
    extra = 0


class LiabilityInline(admin.TabularInline):
    model = Liability
    fk_name = "player"
    extra = 0


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "game", "profession", "track", "position", "cash"]
    list_filter = ["game"]
    readonly_fields = ["token"]
    inlines = [AssetInline, LiabilityInline]


@admin.register(PendingAction)
class PendingActionAdmin(admin.ModelAdmin):
    list_display = ["created_at", "game", "player", "kind", "status"]
    list_filter = ["status", "game"]


@admin.register(GameEvent)
class GameEventAdmin(admin.ModelAdmin):
    list_display = ["seq", "game", "player", "kind", "created_at"]
    list_filter = ["game"]


@admin.register(DeckState)
class DeckStateAdmin(admin.ModelAdmin):
    list_display = ["game", "category", "next_index"]
