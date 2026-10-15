"""Профессии совпадают с карточками из docs/Карточки_профессий_01-12_рубли.md."""

import pytest
from django.core.management import call_command

from game import lobby
from game.finance import rub, statement
from game.models import Profession
from game.seed_data import PROFESSIONS

pytestmark = pytest.mark.django_db

# Итоги из карточек: общие расходы, денежный поток, наличные, вся задолженность.
EXPECTED = {
    "Секретарь": (16_200, 8_800, 15_900, 450_000),
    "Менеджер": (29_300, 16_700, 20_700, 970_000),
    "Водитель грузовика": (16_200, 8_800, 16_300, 450_000),
    "Пилот авиалиний": (69_000, 26_000, 30_000, 1_810_000),
    "Автомеханик": (12_800, 7_200, 13_900, 370_000),
    "Адвокат": (54_200, 20_800, 24_800, 2_110_000),
    "Инженер": (32_100, 16_900, 20_900, 990_000),
    "Учитель": (21_900, 11_100, 15_100, 710_000),
    "Дворник": (9_500, 6_500, 12_100, 270_000),
    "Медсестра": (19_800, 11_200, 16_000, 620_000),
    "Врач": (96_500, 35_500, 39_500, 3_810_000),
    "Офицер полиции": (18_800, 11_200, 16_400, 540_000),
}


def test_professions_match_cards():
    assert {p["name"] for p in PROFESSIONS} == set(EXPECTED)
    for p in PROFESSIONS:
        expenses = p["taxes"] + p["other_expenses"] + sum(li["payment"] for li in p["liabilities"])
        debt = sum(li["balance"] for li in p["liabilities"])
        assert (expenses, p["salary"] - expenses, p["savings"], debt) == EXPECTED[p["name"]], p[
            "name"
        ]


def test_player_starts_with_profession_budget(host, seeded):
    game = lobby.create_game(host, max_players=6)
    for name in "АБВГДЕ":
        lobby.join_game(game, name)
    lobby.start_game(game)
    players = list(game.players.select_related("profession"))
    assert len({p.profession_id for p in players}) == 6  # профессии не повторяются
    for player in players:
        total, flow, cash, _ = EXPECTED[player.profession.name]
        s = statement(player)
        assert (s.total_expenses, s.cashflow, player.cash) == (total, flow, cash)
        assert (s.passive_income, player.children, player.assets.count()) == (0, 0, 0)


def test_seed_renames_old_professions(seeded):
    Profession.objects.filter(name="Офицер полиции").update(name="Полицейский")
    call_command("seed", stdout=None)
    assert not Profession.objects.filter(name="Полицейский").exists()
    assert Profession.objects.count() == len(PROFESSIONS)


def test_rub():
    assert rub(25_000) == "25\xa0000\xa0₽"
    assert rub(-500) == "−500\xa0₽"
    assert rub(0) == "0\xa0₽"
