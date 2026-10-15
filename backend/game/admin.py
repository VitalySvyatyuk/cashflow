import json

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from game.models import (
    CARD_KIND_FIELDS,
    Asset,
    BoardCell,
    Card,
    Category,
    CellType,
    Game,
    GameEvent,
    Liability,
    PendingAction,
    Player,
    Profession,
)


@admin.display(description="цвет")
def color_swatch(obj):
    return format_html(
        '<span style="display:inline-block;width:22px;height:16px;border-radius:3px;'
        'background:{};vertical-align:middle"></span>',
        obj.color,
    )


# Цвет выбирается палитрой, а не вводом кода.
COLOR_WIDGETS = {"color": forms.TextInput(attrs={"type": "color"})}


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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", color_swatch, "deck", "card_count"]

    def get_form(self, request, obj=None, **kwargs):
        return super().get_form(request, obj, widgets=COLOR_WIDGETS, **kwargs)

    @admin.display(description="карточек")
    def card_count(self, obj):
        return obj.cards.count()


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = [
            "category",
            "kind",
            "title",
            "text",
            "is_active",
            "symbol",
            "property_name",
            "price",
            "cost",
            "down_payment",
            "mortgage",
            "cashflow",
            "amount",
        ]
        # Какие поля показывать для выбранного типа — см. card_admin.js.
        widgets = {
            "kind": forms.Select(
                attrs={
                    "data-kind-fields": json.dumps(
                        {
                            k: f + (["mortgage"] if k == "real_estate" else [])
                            for k, f in CARD_KIND_FIELDS.items()
                        }
                    )
                }
            )
        }


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    form = CardForm
    list_display = ["title", "category", "kind", "is_active"]
    list_filter = ["category", "kind", "is_active"]
    list_select_related = ["category"]
    search_fields = ["title", "text", "symbol", "property_name"]
    fieldsets = [
        (None, {"fields": ["category", "kind", "title", "text", "is_active"]}),
        (
            "Параметры",
            {
                "description": "Показаны только поля, нужные для выбранного типа.",
                "fields": [
                    "symbol",
                    "property_name",
                    "price",
                    "cost",
                    "down_payment",
                    "mortgage",
                    "cashflow",
                    "amount",
                ],
            },
        ),
    ]

    class Media:
        js = ["game/card_admin.js"]


@admin.register(CellType)
class CellTypeAdmin(admin.ModelAdmin):
    list_display = ["name", color_swatch, "kind", "cell_count"]

    def get_form(self, request, obj=None, **kwargs):
        return super().get_form(request, obj, widgets=COLOR_WIDGETS, **kwargs)

    @admin.display(description="клеток")
    def cell_count(self, obj):
        return obj.cells.count()


@admin.register(BoardCell)
class BoardCellAdmin(admin.ModelAdmin):
    list_display = ["position", "track", "cell_type", color_swatch, "title"]
    list_filter = ["track", "cell_type"]
    list_select_related = ["cell_type"]


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
