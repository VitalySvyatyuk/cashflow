import pytest

from game import engine, lobby
from game.engine import HOST_ACTOR, Actor, decide, submit_action
from game.errors import GameError
from game.finance import BANK_LOAN_TITLE, statement
from game.models import (
    Asset,
    BoardCell,
    Card,
    CardCategory,
    CellKind,
    Game,
    Liability,
    PendingAction,
    Track,
)

pytestmark = pytest.mark.django_db


class Dice:
    """Подставные кубики: randint выдаёт заранее заданные значения, shuffle ничего не делает."""

    def __init__(self, *values):
        self.values = list(values)

    def randint(self, a, b):
        return self.values.pop(0)

    def shuffle(self, items):
        pass


@pytest.fixture
def started(game, seeded, rnd):
    lobby.join_game(game, "Маша")
    lobby.join_game(game, "Петя")
    lobby.start_game(game, rnd=rnd)
    game.refresh_from_db()
    return game


@pytest.fixture
def masha(started):
    return started.players.get(name="Маша")


@pytest.fixture
def petya(started):
    return started.players.get(name="Петя")


def act(game, player, kind, rnd=None, **params):
    return submit_action(game, Actor(player), kind, params, rnd=rnd)


def host(game, kind, **params):
    return submit_action(game, HOST_ACTOR, kind, params)


def approve(game, pending, **params):
    return decide(game, pending.id, True, params)


def fresh(obj):
    obj.refresh_from_db()
    return obj


def place(player, position, track=Track.RAT_RACE):
    player.track = track
    player.position = position
    player.save()


def cell_position(kind, track=Track.RAT_RACE):
    return BoardCell.objects.filter(track=track, kind=kind).order_by("position")[0].position


def open_card(game, card, phase=Game.Phase.CARD):
    game.current_card = card
    game.phase = phase
    game.save()


def stock_card(price=10):
    return Card.objects.create(
        category=CardCategory.SMALL_DEAL,
        color="#000000",
        title=f"Акции ТСТ по ${price}",
        effect={"type": "stock", "symbol": "ТСТ", "price": price},
    )


def house_card(cost=50000, down=5000, flow=200):
    return Card.objects.create(
        category=CardCategory.SMALL_DEAL,
        color="#000000",
        title=f"Дом 3/2 за {cost}",
        effect={
            "type": "real_estate",
            "property": "Дом 3/2",
            "cost": cost,
            "down_payment": down,
            "mortgage": cost - down,
            "cashflow": flow,
        },
    )


# --- Бросок и движение -----------------------------------------------------------------


def test_roll_moves_and_logs(started, masha):
    place(masha, 23)
    act(started, masha, "roll", rnd=Dice(1))  # через край поля на клетку 0 — «Возможность»

    started.refresh_from_db()
    assert fresh(masha).position == 0
    assert started.dice == [1]
    assert started.phase == Game.Phase.CHOOSE_DEAL
    kinds = list(started.events.order_by("seq").values_list("kind", flat=True))
    assert kinds[-3:] == ["dice_rolled", "moved", "landed"]
    assert started.events.get(kind="dice_rolled").payload["text"] == "Маша выбросил(а) 1"


def test_only_current_player_rolls(started, petya):
    with pytest.raises(GameError, match="не ваш ход"):
        act(started, petya, "roll", rnd=Dice(1))


def test_cannot_roll_twice(started, masha):
    place(masha, cell_position(CellKind.PAYCHECK) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    with pytest.raises(GameError, match="нельзя"):
        act(started, masha, "roll", rnd=Dice(1))


def test_passing_paycheck_pays_cashflow(started, masha):
    place(masha, cell_position(CellKind.PAYCHECK) - 1)
    cash = masha.cash
    flow = statement(masha).cashflow
    act(started, masha, "roll", rnd=Dice(2))  # проходит зарплату, встаёт на «Возможность»
    assert fresh(masha).cash == cash + flow
    assert fresh(started).phase == Game.Phase.CHOOSE_DEAL


def test_doodad_paid_automatically(started, masha):
    place(masha, cell_position(CellKind.DOODAD) - 1)
    masha.cash = 100000
    masha.save()
    act(started, masha, "roll", rnd=Dice(1))
    started.refresh_from_db()
    assert started.phase == Game.Phase.END_TURN
    assert started.current_card.category == CardCategory.DOODAD
    assert fresh(masha).cash == 100000 - started.current_card.effect["amount"]


def test_doodad_takes_auto_loan_when_broke(started, masha):
    masha.cash = 0
    masha.save()
    place(masha, cell_position(CellKind.DOODAD) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    amount = fresh(started).current_card.effect["amount"]
    loan = masha.liabilities.get(title=BANK_LOAN_TITLE)
    assert loan.balance % 1000 == 0 and loan.balance >= amount
    assert loan.payment == loan.balance // 10
    assert fresh(masha).cash == loan.balance - amount
    assert started.events.filter(kind="auto_loan").exists()


def test_baby(started, masha):
    place(masha, cell_position(CellKind.BABY) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    assert fresh(masha).children == 1


def test_downsized_pays_and_skips_turns(started, masha, petya):
    place(masha, cell_position(CellKind.DOWNSIZED) - 1)
    expenses = statement(masha).total_expenses
    masha.cash = expenses + 100
    masha.save()
    act(started, masha, "roll", rnd=Dice(1))
    assert fresh(masha).cash == 100
    assert masha.skip_turns == 2

    act(started, masha, "end_turn")
    assert fresh(started).current_player == petya
    place(petya, cell_position(CellKind.PAYCHECK) - 1)
    act(started, petya, "roll", rnd=Dice(1))
    act(started, petya, "end_turn")
    # Маша пропускает — снова ход Пети
    assert fresh(started).current_player == petya
    assert fresh(masha).skip_turns == 1


# --- Сделки и одобрение ----------------------------------------------------------------


def test_choose_deal_draws_card(started, masha):
    place(masha, 23)
    act(started, masha, "roll", rnd=Dice(1))
    act(started, masha, "choose_deal", size="big")
    started.refresh_from_db()
    assert started.phase == Game.Phase.CARD
    assert started.current_card.category == CardCategory.BIG_DEAL


def test_buy_needs_host_approval(started, masha):
    open_card(started, stock_card(price=10))
    cash = masha.cash
    pending = act(started, masha, "buy", quantity=20)

    assert pending.status == PendingAction.Status.PENDING
    assert pending.description == "купить 20 акц. ТСТ за $200"
    assert fresh(masha).cash == cash  # ничего не изменилось до решения

    approve(started, pending)
    assert fresh(masha).cash == cash - 200
    stock = masha.assets.get()
    assert (stock.kind, stock.key, stock.quantity) == (Asset.Kind.STOCK, "ТСТ", 20)
    assert fresh(started).phase == Game.Phase.END_TURN


def test_host_amends_request(started, masha):
    open_card(started, stock_card(price=10))
    pending = act(started, masha, "buy", quantity=20)
    approve(started, pending, quantity=5)
    assert masha.assets.get().quantity == 5


def test_rejected_request_changes_nothing(started, masha):
    open_card(started, stock_card())
    pending = act(started, masha, "buy", quantity=1)
    decide(started, pending.id, False, comment="подумай ещё")
    assert fresh(pending).status == PendingAction.Status.REJECTED
    assert not masha.assets.exists()
    assert fresh(started).phase == Game.Phase.CARD
    assert "подумай ещё" in started.events.last().payload["text"]


def test_duplicate_request_rejected(started, masha):
    open_card(started, stock_card())
    act(started, masha, "buy", quantity=1)
    with pytest.raises(GameError, match="уже ждёт"):
        act(started, masha, "buy", quantity=2)


def test_cannot_request_without_money(started, masha):
    open_card(started, stock_card(price=10))
    with pytest.raises(GameError, match="Не хватает"):
        act(started, masha, "buy", quantity=masha.cash)


def test_host_acts_for_player_immediately(started, masha):
    open_card(started, stock_card(price=1))
    assert host(started, "buy", quantity=3) is None
    assert masha.assets.get().quantity == 3


def test_buy_real_estate_creates_mortgage(started, masha):
    masha.cash = 10000
    masha.save()
    passive = statement(masha).passive_income
    open_card(started, house_card(cost=50000, down=5000, flow=200))
    approve(started, act(started, masha, "buy"))

    house = masha.assets.get()
    assert house.key == "Дом 3/2"
    assert house.liability.balance == 45000
    assert fresh(masha).cash == 5000
    assert statement(masha).passive_income == passive + 200


def test_pass_cancels_pending_buy(started, masha):
    open_card(started, stock_card())
    pending = act(started, masha, "buy", quantity=1)
    act(started, masha, "pass")
    assert fresh(pending).status == PendingAction.Status.CANCELLED
    assert fresh(started).phase == Game.Phase.END_TURN


def test_approval_fails_if_turn_moved_on(started, masha):
    pending = act(started, masha, "take_loan", amount=1000)  # не привязана к фазе
    open_card(started, stock_card())
    buy = act(started, masha, "buy", quantity=1)
    host(started, "next_turn")
    assert fresh(buy).status == PendingAction.Status.CANCELLED
    approve(started, pending)  # кредит всё ещё можно одобрить
    assert masha.liabilities.filter(title=BANK_LOAN_TITLE).exists()


# --- Продажа ---------------------------------------------------------------------------


def test_other_player_sells_stock_on_card(started, masha, petya):
    Asset.objects.create(player=petya, kind=Asset.Kind.STOCK, title="ТСТ", key="ТСТ", quantity=10)
    open_card(started, stock_card(price=30))
    cash = petya.cash
    pending = act(started, petya, "sell", asset_id=petya.assets.get().id, quantity=4)
    approve(started, pending)
    assert fresh(petya).cash == cash + 120
    assert petya.assets.get().quantity == 6


def test_sell_property_pays_off_mortgage(started, masha, petya):
    house = Asset.objects.create(
        player=petya, kind=Asset.Kind.REAL_ESTATE, title="Дом 3/2", key="Дом 3/2"
    )
    mortgage = Liability.objects.create(
        player=petya, title="Ипотека: Дом 3/2", balance=45000, payment=0, asset=house
    )
    offer = Card.objects.create(
        category=CardCategory.MARKET,
        color="#000000",
        title="Покупатель",
        effect={"type": "sell_offer", "property": "Дом 3/2", "price": 70000},
    )
    open_card(started, offer)
    cash = petya.cash
    approve(started, act(started, petya, "sell", asset_id=house.id))
    assert fresh(petya).cash == cash + 25000
    assert not petya.assets.exists()
    assert not Liability.objects.filter(id=mortgage.id).exists()


def test_sell_wrong_asset_rejected(started, petya):
    house = Asset.objects.create(
        player=petya, kind=Asset.Kind.REAL_ESTATE, title="Дуплекс", key="Дуплекс"
    )
    open_card(started, stock_card())
    with pytest.raises(GameError):
        act(started, petya, "sell", asset_id=house.id)


# --- Благотворительность ---------------------------------------------------------------


def test_charity_gives_extra_dice(started, masha):
    masha.cash = 100000
    masha.save()
    place(masha, cell_position(CellKind.CHARITY) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    assert fresh(started).phase == Game.Phase.CHARITY

    amount = statement(masha).total_income // 10
    cash = fresh(masha).cash
    approve(started, act(started, masha, "charity"))
    assert fresh(masha).cash == cash - amount
    assert masha.charity_turns == 3

    started.phase = Game.Phase.ROLL
    started.save()
    with pytest.raises(GameError, match="от 1 до 2"):
        act(started, masha, "roll", rnd=Dice(1, 1, 1), dice=3)
    place(masha, 0)
    act(started, masha, "roll", rnd=Dice(1, 1), dice=2)
    assert fresh(started).dice == [1, 1]
    assert fresh(masha).charity_turns == 2


# --- Кредиты ---------------------------------------------------------------------------


def test_loans(started, masha):
    cash = masha.cash
    with pytest.raises(GameError, match="кратными"):
        act(started, masha, "take_loan", amount=1500)
    approve(started, act(started, masha, "take_loan", amount=5000))
    loan = masha.liabilities.get(title=BANK_LOAN_TITLE)
    assert (loan.balance, loan.payment, fresh(masha).cash) == (5000, 500, cash + 5000)

    approve(started, act(started, masha, "repay_loan", liability_id=loan.id, amount=2000))
    assert (fresh(loan).balance, loan.payment) == (3000, 300)
    approve(started, act(started, masha, "repay_loan", liability_id=loan.id, amount=3000))
    assert not masha.liabilities.filter(title=BANK_LOAN_TITLE).exists()


def test_profession_debt_repaid_only_in_full(started, masha):
    debt = masha.liabilities.exclude(title=BANK_LOAN_TITLE).order_by("balance").first()
    masha.cash = debt.balance
    masha.save()
    with pytest.raises(GameError, match="целиком"):
        act(started, masha, "repay_loan", liability_id=debt.id, amount=debt.balance - 1)
    approve(started, act(started, masha, "repay_loan", liability_id=debt.id, amount=debt.balance))
    assert not masha.liabilities.filter(id=debt.id).exists()


def test_other_player_can_take_loan_any_time(started, petya):
    assert act(started, petya, "take_loan", amount=1000).status == PendingAction.Status.PENDING


# --- Ведущий ---------------------------------------------------------------------------


def test_pause_blocks_players(started, masha):
    host(started, "pause")
    assert fresh(started).status == Game.Status.PAUSED
    with pytest.raises(GameError, match="паузе"):
        act(started, masha, "roll", rnd=Dice(1))
    host(started, "adjust_cash", player_id=masha.id, amount=100)  # ведущий может
    host(started, "resume")
    place(masha, cell_position(CellKind.PAYCHECK) - 1)
    act(started, masha, "roll", rnd=Dice(1))


def test_players_cannot_use_host_actions(started, masha):
    for kind in ("pause", "undo", "adjust_cash", "next_turn"):
        with pytest.raises(GameError, match="ведущий"):
            act(started, masha, kind, amount=1)


def test_adjust_cash(started, petya):
    cash = petya.cash
    host(started, "adjust_cash", player_id=petya.id, amount=-300, reason="штраф")
    assert fresh(petya).cash == cash - 300
    assert "штраф" in started.events.last().payload["text"]


def test_undo_restores_previous_state(started, masha):
    open_card(started, stock_card(price=10))
    cash = masha.cash
    approve(started, act(started, masha, "buy", quantity=10))
    assert masha.assets.exists()

    host(started, "undo")
    started.refresh_from_db()
    assert fresh(masha).cash == cash
    assert not masha.assets.exists()
    assert started.phase == Game.Phase.CARD
    assert started.events.last().kind == "undone"


def test_undo_restores_liabilities_and_turn(started, masha, petya):
    place(masha, cell_position(CellKind.PAYCHECK) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    approve(started, act(started, masha, "take_loan", amount=2000))
    act(started, masha, "end_turn")
    assert fresh(started).current_player == petya

    host(started, "undo")  # конец хода
    host(started, "undo")  # кредит
    assert fresh(started).current_player == masha
    assert not masha.liabilities.filter(title=BANK_LOAN_TITLE).exists()


def test_undo_does_not_lift_pause(started, masha):
    host(started, "adjust_cash", player_id=masha.id, amount=100)
    host(started, "pause")
    host(started, "undo")
    assert fresh(started).status == Game.Status.PAUSED


def test_nothing_to_undo(started):
    with pytest.raises(GameError, match="Нечего"):
        host(started, "undo")


# --- Скоростная дорожка ----------------------------------------------------------------


def make_rich(player):
    Asset.objects.create(
        player=player,
        kind=Asset.Kind.BUSINESS,
        title="Завод",
        cashflow=statement(player).total_expenses + 1,
    )


def test_fast_track_requires_passive_income(started, masha):
    started.phase = Game.Phase.END_TURN
    started.save()
    with pytest.raises(GameError, match="Пассивный"):
        act(started, masha, "go_fast_track")

    make_rich(masha)
    passive = statement(masha).passive_income
    approve(started, act(started, masha, "go_fast_track"))
    masha.refresh_from_db()
    assert masha.track == Track.FAST_TRACK
    assert masha.fast_track_income == passive * 100


def test_fast_track_dream_wins_and_undo_reopens(started, masha):
    place(masha, cell_position(CellKind.DREAM, Track.FAST_TRACK) - 1, Track.FAST_TRACK)
    masha.cash = 10_000_000
    masha.save()
    act(started, masha, "roll", rnd=Dice(1, 0))  # на скоростной дорожке 2 кубика
    assert fresh(started).phase == Game.Phase.DREAM

    approve(started, act(started, masha, "buy_dream"))
    started.refresh_from_db()
    assert started.status == Game.Status.FINISHED
    assert started.winner == masha
    with pytest.raises(GameError, match="завершена"):
        act(started, masha, "end_turn")

    host(started, "undo")
    assert fresh(started).status == Game.Status.RUNNING
    assert started.winner is None


def test_fast_track_business(started, masha):
    place(masha, cell_position(CellKind.BUSINESS, Track.FAST_TRACK) - 1, Track.FAST_TRACK)
    masha.cash = 10_000_000
    masha.save()
    act(started, masha, "roll", rnd=Dice(1, 0))
    cell = BoardCell.objects.get(track=Track.FAST_TRACK, position=fresh(masha).position)
    approve(started, act(started, masha, "buy_business"))
    assert fresh(masha).fast_track_income == cell.effect["cashflow"]


# --- Колоды ----------------------------------------------------------------------------


def test_deck_reshuffles_when_exhausted(started, masha):
    deck = started.decks.get(category=CardCategory.DOODAD)
    deck.next_index = len(deck.card_ids)
    deck.save()
    place(masha, cell_position(CellKind.DOODAD) - 1)
    masha.cash = 100000
    masha.save()
    act(started, masha, "roll", rnd=Dice(1))
    assert fresh(deck).next_index == 1


def test_unknown_action(started, masha):
    with pytest.raises(GameError, match="Неизвестное"):
        act(started, masha, "fly")


def test_bad_params(started, masha):
    open_card(started, stock_card())
    with pytest.raises(GameError, match="quantity"):
        act(started, masha, "buy", quantity="много")
    with pytest.raises(GameError):
        act(started, masha, "buy", quantity=0)


def test_actions_registry_is_consistent():
    for kind, action in engine.ACTIONS.items():
        assert action.policy in (engine.AUTO, engine.APPROVE, engine.HOST), kind
        if action.policy == engine.APPROVE:
            assert action.describe is not None, kind
