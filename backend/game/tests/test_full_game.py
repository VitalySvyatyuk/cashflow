"""Полная партия на 4 игроков, которую играет бот.

Ловит ошибки на стыках правил: после каждого действия проверяем инварианты,
а время от времени — что «отменить» возвращает игру точно в прежнее состояние.
"""

import random

import pytest

from game import lobby
from game.engine import HOST_ACTOR, Actor, decide, submit_action
from game.errors import GameError
from game.finance import BANK_LOAN_TITLE, statement
from game.models import Asset, BoardCell, Game, PendingAction, Track
from game.state import build_state

pytestmark = pytest.mark.django_db

MAX_TURNS = 600
UNDO_EVERY = 25


class Bot:
    def __init__(self, game, seed):
        self.game = game
        self.rnd = random.Random(seed)
        self.actions = 0
        self.undo_checks = 0
        self.track_size = {track: BoardCell.objects.filter(track=track).count() for track in Track}

    # --- выполнение действий ---------------------------------------------------------

    def act(self, player, kind, **params):
        """Игрок делает действие; если нужна санкция — ведущий одобряет."""
        self.actions += 1
        check_undo = self.actions % UNDO_EVERY == 0
        before = fingerprint(self.game) if check_undo else None

        pending = submit_action(self.game, Actor(player), kind, params, rnd=self.rnd)
        if pending is not None:
            decide(self.game, pending.id, True, rnd=self.rnd)

        if check_undo:
            # Отменяем и проверяем, что всё вернулось, затем повторяем то же действие.
            submit_action(self.game, HOST_ACTOR, "undo")
            after = fingerprint(self.game)
            assert after == before, f"undo после {kind} не вернул состояние"
            self.undo_checks += 1
            pending = submit_action(self.game, Actor(player), kind, params, rnd=self.rnd)
            if pending is not None:
                decide(self.game, pending.id, True, rnd=self.rnd)

        self.game.refresh_from_db()
        check_invariants(self.game, self.track_size)

    def try_act(self, player, kind, **params):
        try:
            self.act(player, kind, **params)
            return True
        except GameError:
            return False

    # --- стратегия -----------------------------------------------------------------------

    def play_turn(self):
        game = self.game
        player = game.current_player
        self.act(player, "roll", dice=self.rnd.choice([1, 2, 3]))

        for _ in range(10):  # фаза меняется после каждого решения
            game.refresh_from_db()
            if game.status == Game.Status.FINISHED:
                return
            player.refresh_from_db()
            phase = game.phase
            if phase == Game.Phase.CHOOSE_DEAL:
                size = "big" if player.cash > 30000 else "small"
                self.act(player, "choose_deal", size=size)
            elif phase == Game.Phase.CARD:
                self.handle_card(player)
            elif phase == Game.Phase.CHARITY:
                if not self.try_act(player, "charity"):
                    self.act(player, "pass")
            elif phase == Game.Phase.BUSINESS:
                if not self.try_act(player, "buy_business"):
                    self.act(player, "pass")
            elif phase == Game.Phase.DREAM:
                if not self.try_act(player, "buy_dream"):
                    self.act(player, "pass")
            elif phase == Game.Phase.END_TURN:
                self.finish_turn(player)
                return
        raise AssertionError(f"ход застрял в фазе {game.phase}")

    def handle_card(self, player):
        card = self.game.current_card
        effect = card.effect
        # Сначала все, у кого есть что продать, продают.
        for owner in self.game.players.all():
            for asset in owner.assets.all():
                self.try_act(owner, "sell", asset_id=asset.id, quantity=asset.quantity)
        if (
            effect.get("type") == "stock"
            and effect["price"] <= 10
            and player.cash >= effect["price"]
        ):
            self.act(player, "buy", quantity=min(player.cash // effect["price"], 500))
        elif effect.get("type") == "real_estate" and effect["cashflow"] > 0:
            # Берём кредит на взнос, если сделка окупает проценты.
            short = effect["down_payment"] - player.cash
            loan = -(-short // 1000) * 1000 if short > 0 else 0
            if loan == 0 or effect["cashflow"] > loan // 10:
                if loan:
                    self.act(player, "take_loan", amount=loan)
                self.act(player, "buy")
        self.game.refresh_from_db()
        if self.game.phase == Game.Phase.CARD:
            self.act(player, "pass")

    def finish_turn(self, player):
        if player.track == Track.RAT_RACE and statement(player).can_exit_rat_race:
            self.act(player, "go_fast_track")
        player.refresh_from_db()
        loan = player.liabilities.filter(title=BANK_LOAN_TITLE).first()
        if loan and player.cash > 5000:
            amount = min(loan.balance, (player.cash - 5000) // 1000 * 1000)
            if amount:
                self.act(player, "repay_loan", liability_id=loan.id, amount=amount)
        self.act(player, "end_turn")


def fingerprint(game):
    """Всё изменяемое состояние игры, кроме журнала и заявок."""
    state = build_state(game.id)
    return {k: v for k, v in state.items() if k not in ("events", "pending_actions")}


def check_invariants(game, track_size):
    state = build_state(game.id)  # заодно проверяем, что состояние сериализуется
    assert state["status"] in Game.Status.values
    assert not game.pending_actions.filter(status=PendingAction.Status.PENDING).exists()

    seqs = list(game.events.order_by("seq").values_list("seq", flat=True))
    assert seqs == list(range(1, len(seqs) + 1)), "дыра в журнале"

    for deck in game.decks.all():
        assert deck.next_index <= len(deck.card_ids)

    for player in game.players.all():
        assert player.cash >= 0, f"{player}: отрицательные наличные {player.cash}"
        assert 0 <= player.position < track_size[player.track]
        for asset in player.assets.all():
            assert asset.quantity > 0
            assert asset.kind in Asset.Kind.values
        for liability in player.liabilities.all():
            assert liability.balance > 0, f"{player}: пустой долг «{liability.title}»"
        s = statement(player)
        assert s.cashflow == s.total_income - s.total_expenses


# Две партии в обычном прогоне, остальные — в make test-all (каждая ~20 секунд).
@pytest.mark.parametrize(
    "seed", [0, 4, *(pytest.param(s, marks=pytest.mark.slow) for s in (1, 2, 3))]
)
def test_bot_plays_full_game(host, seeded, seed):
    game = lobby.create_game(host, max_players=4)
    for name in ("Маша", "Петя", "Аня", "Олег"):
        lobby.join_game(game, name)
    lobby.start_game(game, rnd=random.Random(seed))
    game.refresh_from_db()

    bot = Bot(game, seed)
    for _ in range(MAX_TURNS):
        bot.play_turn()
        game.refresh_from_db()
        if game.status == Game.Status.FINISHED:
            break

    print(
        f"\nseed={seed}: ходов {game.turn_number}, действий {bot.actions}, "
        f"проверок отмены {bot.undo_checks}, победитель {game.winner}, "
        f"на скоростной: {game.players.filter(track=Track.FAST_TRACK).count()}"
    )
    assert game.status == Game.Status.FINISHED, f"за {MAX_TURNS} ходов никто не победил"
    assert game.winner.track == Track.FAST_TRACK
    assert bot.undo_checks > 0
    assert game.events.filter(kind="fast_track").exists()
