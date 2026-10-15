import pytest

from game import engine, lobby
from game.engine import HOST_ACTOR, Actor, decide, submit_action
from game.errors import GameError
from game.finance import BANK_LOAN_STEP, BANK_LOAN_TITLE, statement
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
        title=f"Акции ТСТ по {price} ₽",
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


def test_passing_paycheck_waits_for_collect(started, masha, petya):
    place(masha, cell_position(CellKind.PAYCHECK) - 1)
    cash = masha.cash
    flow = statement(masha).cashflow
    act(started, masha, "roll", rnd=Dice(2))  # проходит «Доход», встаёт на «Возможность»
    started.refresh_from_db()
    assert (started.phase, started.paydays) == (Game.Phase.INCOME, 1)
    assert fresh(masha).cash == cash  # пока не нажал «Получить»
    assert started.events.filter(kind="landed").count() == 1
    with pytest.raises(GameError, match="нельзя"):
        act(started, masha, "end_turn")
    with pytest.raises(GameError, match="не ваш ход"):
        act(started, petya, "collect_income")

    act(started, masha, "collect_income")
    started.refresh_from_db()
    assert fresh(masha).cash == cash + flow
    assert (started.phase, started.paydays) == (Game.Phase.CHOOSE_DEAL, 0)  # клетка сработала
    assert started.events.filter(kind="landed").count() == 1  # без повторного объявления


def test_two_paychecks_in_one_move(started, masha):
    cells = list(
        BoardCell.objects.filter(track=Track.RAT_RACE, kind=CellKind.PAYCHECK).values_list(
            "position", flat=True
        )
    )
    first, second = cells[0], cells[1]
    place(masha, first - 1)
    masha.charity_turns = 1  # два кубика — только после благотворительности
    masha.save()
    cash, flow = masha.cash, statement(masha).cashflow
    steps = second - first + 1  # встаёт прямо на второй «Доход»
    act(started, masha, "roll", rnd=Dice(6, steps - 6), dice=2)
    assert fresh(started).paydays == 2
    act(started, masha, "collect_income")
    assert fresh(masha).cash == cash + 2 * flow


def test_landing_without_paycheck_skips_income(started, masha):
    place(masha, cell_position(CellKind.PAYCHECK))  # уже стоит на «Доходе»
    act(started, masha, "roll", rnd=Dice(1))
    assert fresh(started).phase == Game.Phase.CHOOSE_DEAL


def test_doodad_waits_for_player_to_pay(started, masha):
    place(masha, cell_position(CellKind.DOODAD) - 1)
    masha.cash = 100000
    masha.save()
    act(started, masha, "roll", rnd=Dice(1))
    started.refresh_from_db()
    assert started.phase == Game.Phase.PAY
    assert started.current_card.category == CardCategory.DOODAD
    assert fresh(masha).cash == 100000  # пока не нажал «Заплатить»
    for kind in ("pass", "end_turn"):
        with pytest.raises(GameError, match="нельзя"):
            act(started, masha, kind)

    act(started, masha, "pay_card")
    started.refresh_from_db()
    assert started.phase == Game.Phase.END_TURN
    assert fresh(masha).cash == 100000 - started.current_card.effect["amount"]
    assert started.events.filter(kind="paid").exists()


def test_only_current_player_pays(started, masha, petya):
    place(masha, cell_position(CellKind.DOODAD) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    with pytest.raises(GameError, match="не ваш ход"):
        act(started, petya, "pay_card")
    host(started, "pay_card")  # ведущий может заплатить за игрока
    assert fresh(started).phase == Game.Phase.END_TURN


def test_doodad_takes_auto_loan_when_broke(started, masha):
    masha.cash = 0
    masha.save()
    place(masha, cell_position(CellKind.DOODAD) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    act(started, masha, "pay_card")
    amount = fresh(started).current_card.effect["amount"]
    loan = masha.liabilities.get(title=BANK_LOAN_TITLE)
    assert loan.balance % BANK_LOAN_STEP == 0 and loan.balance >= amount
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
    act(started, petya, "collect_income")
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


def test_buy_stock_without_approval(started, masha):
    open_card(started, stock_card(price=10))
    cash = masha.cash
    assert act(started, masha, "buy", quantity=20) is None

    assert not started.pending_actions.exists()
    assert fresh(masha).cash == cash - 200
    stock = masha.assets.get()
    assert (stock.kind, stock.key, stock.quantity) == (Asset.Kind.STOCK, "ТСТ", 20)
    assert fresh(started).phase == Game.Phase.END_TURN


def test_buy_property_needs_host_approval(started, masha):
    masha.cash = 10_000
    masha.save()
    open_card(started, house_card(down=5000))
    pending = act(started, masha, "buy")

    assert pending.status == PendingAction.Status.PENDING
    assert pending.description == "купить «Дом 3/2 за 50000», взнос 5\xa0000\xa0₽"
    assert fresh(masha).cash == 10_000  # ничего не изменилось до решения

    approve(started, pending)
    assert fresh(masha).cash == 5000
    assert masha.assets.get().kind == Asset.Kind.REAL_ESTATE


def test_host_amends_request(started, masha):
    pending = act(started, masha, "take_loan", amount=50_000)
    approve(started, pending, amount=20_000)
    assert masha.liabilities.get(title=BANK_LOAN_TITLE).balance == 20_000


def test_rejected_request_changes_nothing(started, masha):
    open_card(started, house_card())
    pending = act(started, masha, "buy")
    decide(started, pending.id, False, comment="подумай ещё")
    assert fresh(pending).status == PendingAction.Status.REJECTED
    assert not masha.assets.exists()
    assert fresh(started).phase == Game.Phase.CARD
    assert "подумай ещё" in started.events.last().payload["text"]


def test_duplicate_request_rejected(started, masha):
    open_card(started, house_card())
    act(started, masha, "buy")
    with pytest.raises(GameError, match="уже ждёт"):
        act(started, masha, "buy")


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


def test_pass_cancels_pending_buy(started, masha, petya):
    open_card(started, house_card())
    pending = act(started, masha, "buy")
    act(started, masha, "pass")
    assert fresh(pending).status == PendingAction.Status.CANCELLED
    assert fresh(started).offer_player == petya  # дом предлагают следующему


@pytest.fixture
def trio(game, seeded, rnd):
    """Игра на троих: Маша, Петя, Вася — по порядку мест."""
    for name in ("Маша", "Петя", "Вася"):
        lobby.join_game(game, name)
    lobby.start_game(game, rnd=rnd)
    game.refresh_from_db()
    return game, *(game.players.get(name=n) for n in ("Маша", "Петя", "Вася"))


def test_declined_property_offered_around_the_table(trio):
    started, masha, petya, vasya = trio
    open_card(started, house_card())
    act(started, masha, "pass")
    started.refresh_from_db()
    assert started.phase == Game.Phase.CARD
    assert started.offer_player == petya
    assert started.events.filter(kind="offered", player=petya).exists()

    with pytest.raises(GameError, match="не ваш ход"):
        act(started, masha, "buy")
    with pytest.raises(GameError, match="не ваш ход"):
        act(started, vasya, "pass")

    act(started, petya, "pass")
    assert fresh(started).offer_player == vasya
    act(started, vasya, "pass")
    started.refresh_from_db()
    assert started.offer_player is None
    assert started.phase == Game.Phase.END_TURN
    assert started.current_player == masha
    assert started.events.filter(kind="offer_declined").exists()


def test_offered_player_buys_property(started, masha, petya):
    petya.cash = 10_000
    petya.save()
    open_card(started, house_card(down=5000))
    act(started, masha, "pass")
    pending = act(started, petya, "buy")
    approve(started, pending)

    started.refresh_from_db()
    assert started.offer_player is None
    assert started.phase == Game.Phase.END_TURN
    assert started.current_player == masha
    assert fresh(petya).cash == 5000
    assert petya.assets.get().liability.balance == 45000
    assert not masha.assets.exists()
    act(started, masha, "end_turn")
    assert fresh(started).current_player == petya


def test_host_acts_for_offered_player(started, masha, petya):
    petya.cash = 10_000
    petya.save()
    open_card(started, house_card())
    act(started, masha, "pass")
    host(started, "buy")  # без player_id — за того, кому предложено
    assert petya.assets.exists()


def test_offer_reaches_seats_before_current(trio):
    started, masha, petya, vasya = trio
    act(started, masha, "roll", rnd=Dice(1))
    started.refresh_from_db()
    started.phase = Game.Phase.END_TURN
    started.save()
    act(started, masha, "end_turn")
    open_card(fresh(started), house_card())
    act(started, petya, "pass")
    assert fresh(started).offer_player == vasya
    act(started, vasya, "pass")
    assert fresh(started).offer_player == masha


def test_offer_skips_fast_track_players(trio):
    started, masha, petya, vasya = trio
    place(petya, 0, Track.FAST_TRACK)
    open_card(started, house_card())
    act(started, masha, "pass")
    assert fresh(started).offer_player == vasya


def test_stock_and_market_cards_not_offered(started, masha, petya):
    open_card(started, stock_card())
    act(started, masha, "pass")
    started.refresh_from_db()
    assert started.offer_player is None
    assert started.phase == Game.Phase.END_TURN


def test_undo_returns_offer_to_previous_player(started, masha, petya):
    open_card(started, house_card())
    act(started, masha, "pass")
    host(started, "undo")
    started.refresh_from_db()
    assert started.offer_player is None
    assert started.phase == Game.Phase.CARD


def test_next_turn_drops_offer(started, masha, petya):
    open_card(started, house_card())
    act(started, masha, "pass")
    host(started, "next_turn")
    started.refresh_from_db()
    assert started.offer_player is None
    assert started.current_player == petya


def test_approval_fails_if_turn_moved_on(started, masha):
    pending = act(started, masha, "take_loan", amount=10_000)  # не привязана к фазе
    open_card(started, house_card())
    buy = act(started, masha, "buy")
    host(started, "next_turn")
    assert fresh(buy).status == PendingAction.Status.CANCELLED
    approve(started, pending)  # кредит всё ещё можно одобрить
    assert masha.liabilities.filter(title=BANK_LOAN_TITLE).exists()


# --- Продажа ---------------------------------------------------------------------------


def draw_stock(game, player, price=30):
    """Игрок выбирает малую сделку и вытягивает карточку акций ТСТ."""
    card = stock_card(price=price)
    deck = game.decks.get(category=CardCategory.SMALL_DEAL)
    deck.card_ids, deck.next_index = [card.id], 0
    deck.save()
    game.phase = Game.Phase.CHOOSE_DEAL
    game.save()
    act(game, player, "choose_deal", size="small")
    return card


def give_stock(player, quantity=10):
    return Asset.objects.create(
        player=player, kind=Asset.Kind.STOCK, title="Акции ТСТ", key="ТСТ", quantity=quantity
    )


def test_stock_card_waits_for_holders(trio):
    started, masha, petya, vasya = trio
    give_stock(petya)
    draw_stock(started, masha, price=30)
    started.refresh_from_db()
    assert started.stock_waiting == [petya.id]  # у Васи акций нет — его не ждём

    act(started, masha, "buy", quantity=5)
    assert fresh(started).phase == Game.Phase.END_TURN
    with pytest.raises(GameError, match="Ждём решения по акциям: Петя"):
        act(started, masha, "end_turn")

    cash = petya.cash
    act(started, petya, "sell", asset_id=petya.assets.get().id, quantity=3)
    assert fresh(petya).cash == cash + 90
    assert petya.assets.get().quantity == 7
    assert fresh(started).stock_waiting == []
    act(started, masha, "end_turn")
    assert fresh(started).current_player == petya


def test_holder_declines_to_sell(started, masha, petya):
    stock = give_stock(petya)
    draw_stock(started, masha)
    act(started, masha, "pass")
    act(started, petya, "decline_sell")
    assert fresh(started).stock_waiting == []
    assert fresh(stock).quantity == 10
    with pytest.raises(GameError, match="только пока"):
        act(started, petya, "sell", asset_id=stock.id, quantity=1)
    with pytest.raises(GameError, match="не ждут"):
        act(started, petya, "decline_sell")
    act(started, masha, "end_turn")


def test_drawer_sells_own_stock_from_card(started, masha, petya):
    stock = give_stock(masha, 4)
    draw_stock(started, masha, price=30)
    assert fresh(started).stock_waiting == []
    cash = masha.cash
    act(started, masha, "sell", asset_id=stock.id, quantity=4)
    assert fresh(masha).cash == cash + 120
    assert not masha.assets.exists()


def test_next_turn_stops_waiting_for_stock(started, masha, petya):
    give_stock(petya)
    draw_stock(started, masha)
    host(started, "next_turn")
    assert fresh(started).stock_waiting == []


def test_undo_restores_stock_waiting(started, masha, petya):
    give_stock(petya)
    draw_stock(started, masha)
    act(started, petya, "decline_sell")
    host(started, "undo")
    assert fresh(started).stock_waiting == [petya.id]


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


def test_charity(started, masha):
    masha.cash = 100000
    masha.save()
    place(masha, cell_position(CellKind.CHARITY) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    assert fresh(started).phase == Game.Phase.CHARITY

    amount = statement(masha).total_income // 10
    cash = fresh(masha).cash
    approve(started, act(started, masha, "charity"))
    assert fresh(masha).cash == cash - amount
    assert fresh(started).phase == Game.Phase.END_TURN


def roll_with(game, player, count):
    return act(game, player, "roll", rnd=Dice(*[1] * count), dice=count)


def test_rat_race_rolls_one_die(started, masha):
    place(masha, 0)
    roll_with(started, masha, 1)
    assert fresh(started).dice == [1]
    assert fresh(masha).position == 1


@pytest.mark.parametrize("count", [0, 2, 3, 4])
def test_rat_race_has_no_dice_choice(started, masha, count):
    with pytest.raises(GameError, match="только 1 кубик|маленькое"):
        roll_with(started, masha, count)


def test_charity_on_rat_race_gives_one_or_two_dice_for_three_turns(started, masha):
    masha.cash = 100000
    masha.save()
    place(masha, cell_position(CellKind.CHARITY) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    approve(started, act(started, masha, "charity"))
    masha.refresh_from_db()
    assert masha.dice_options() == [1, 2]
    started.phase = Game.Phase.ROLL
    started.save()
    with pytest.raises(GameError, match="1 или 2"):
        roll_with(started, masha, 3)

    for _ in range(3):
        started.phase = Game.Phase.ROLL
        started.save()
        roll_with(started, masha, 2)
    started.phase = Game.Phase.ROLL
    started.save()
    assert fresh(masha).dice_options() == [1]
    with pytest.raises(GameError, match="только 1 кубик"):
        roll_with(started, masha, 2)


def test_fast_track_rolls_two_dice(started, masha):
    place(masha, 0, Track.FAST_TRACK)
    act(started, masha, "roll", rnd=Dice(1, 1))
    assert fresh(started).dice == [1, 1]
    with pytest.raises(GameError, match="только 2 кубика"):
        started.phase = Game.Phase.ROLL
        started.save()
        roll_with(started, masha, 1)


def test_charity_on_fast_track_gives_dice_choice_for_rest_of_game(started, masha):
    place(masha, cell_position(CellKind.CHARITY, Track.FAST_TRACK), Track.FAST_TRACK)
    masha.cash = 10_000_000
    masha.save()
    started.phase = Game.Phase.CHARITY
    started.save()
    approve(started, act(started, masha, "charity"))
    masha.refresh_from_db()
    assert masha.fast_track_charity
    assert masha.charity_turns == 0
    for count in (1, 2, 3, 3, 1):
        started.phase = Game.Phase.ROLL
        started.save()
        roll_with(started, masha, count)
        assert len(fresh(started).dice) == count
    assert fresh(masha).dice_options() == [1, 2, 3]


def test_undo_restores_fast_track_charity(started, masha):
    place(masha, cell_position(CellKind.CHARITY, Track.FAST_TRACK), Track.FAST_TRACK)
    masha.cash = 10_000_000
    masha.save()
    started.phase = Game.Phase.CHARITY
    started.save()
    host(started, "charity")
    assert fresh(masha).fast_track_charity
    host(started, "undo")
    assert not fresh(masha).fast_track_charity


# --- Кредиты ---------------------------------------------------------------------------


def test_loans(started, masha):
    cash = masha.cash
    with pytest.raises(GameError, match="кратными"):
        act(started, masha, "take_loan", amount=15_000)
    approve(started, act(started, masha, "take_loan", amount=50_000))
    loan = masha.liabilities.get(title=BANK_LOAN_TITLE)
    assert (loan.balance, loan.payment, fresh(masha).cash) == (50_000, 5000, cash + 50_000)

    approve(started, act(started, masha, "repay_loan", liability_id=loan.id, amount=20_000))
    assert (fresh(loan).balance, loan.payment) == (30_000, 3000)
    approve(started, act(started, masha, "repay_loan", liability_id=loan.id, amount=30_000))
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
    assert act(started, petya, "take_loan", amount=10_000).status == PendingAction.Status.PENDING


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
    act(started, masha, "buy", quantity=10)
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
    act(started, masha, "collect_income")
    approve(started, act(started, masha, "take_loan", amount=20_000))
    act(started, masha, "end_turn")
    assert fresh(started).current_player == petya

    host(started, "undo")  # конец хода
    host(started, "undo")  # кредит
    host(started, "undo")  # доход
    assert fresh(started).phase == Game.Phase.INCOME
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


def test_host_moves_player_to_fast_track(started, masha):
    started.phase = Game.Phase.END_TURN
    started.save()
    with pytest.raises(GameError, match="пассивный доход"):
        host(started, "go_fast_track", player_id=masha.id)

    make_rich(masha)
    passive = statement(masha).passive_income
    host(started, "go_fast_track", player_id=masha.id)
    masha.refresh_from_db()
    assert masha.track == Track.FAST_TRACK
    assert masha.fast_track_income == passive * 100
    with pytest.raises(GameError, match="уже в большом круге"):
        host(started, "go_fast_track", player_id=masha.id)


def test_player_cannot_move_to_fast_track_alone(started, masha):
    """Игрок только говорит ведущему — перевод делает ведущий."""
    make_rich(masha)
    started.phase = Game.Phase.END_TURN
    started.save()
    with pytest.raises(GameError, match="только ведущий"):
        act(started, masha, "go_fast_track")


def test_fast_track_waits_for_turn_end(started, masha, petya):
    make_rich(masha)
    make_rich(petya)
    open_card(started, stock_card())
    with pytest.raises(GameError, match="закончит ход"):
        host(started, "go_fast_track", player_id=masha.id)
    host(started, "go_fast_track", player_id=petya.id)  # не его ход — можно сразу
    assert fresh(petya).track == Track.FAST_TRACK


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


def test_declined_business_offered_to_fast_track_players(started, masha, petya):
    position = cell_position(CellKind.BUSINESS, Track.FAST_TRACK)
    place(masha, position, Track.FAST_TRACK)
    place(petya, 0, Track.FAST_TRACK)
    petya.cash = 10_000_000
    petya.save()
    started.phase = Game.Phase.BUSINESS
    started.save()
    cell = BoardCell.objects.get(track=Track.FAST_TRACK, position=position)

    act(started, masha, "pass")
    assert fresh(started).offer_player == petya
    approve(started, act(started, petya, "buy_business"))
    assert fresh(petya).fast_track_income == cell.effect["cashflow"]
    assert petya.assets.get().title == cell.title
    assert fresh(started).phase == Game.Phase.END_TURN


def test_declined_business_not_offered_to_rat_race(started, masha, petya):
    place(masha, cell_position(CellKind.BUSINESS, Track.FAST_TRACK), Track.FAST_TRACK)
    started.phase = Game.Phase.BUSINESS
    started.save()
    act(started, masha, "pass")
    started.refresh_from_db()
    assert started.offer_player is None
    assert started.phase == Game.Phase.END_TURN


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


def test_engine_rereads_stale_player(started, masha):
    """Проверки правил идут по свежим данным, а не по устаревшему объекту."""
    stale = started.players.get(id=masha.id)
    masha.cash = 0
    masha.save()
    open_card(started, stock_card(price=1))
    with pytest.raises(GameError, match="Не хватает"):
        act(started, stale, "buy", quantity=1)


def test_player_from_other_game_rejected(started, host):
    other = lobby.create_game(host, 2)
    stranger = lobby.join_game(other, "Чужой")
    with pytest.raises(GameError, match="нет в этой игре"):
        act(started, stranger, "take_loan", amount=10_000)


# --- Завершение игры -------------------------------------------------------------------


def test_host_finishes_game(started, masha):
    pending = act(started, masha, "take_loan", amount=10_000)
    host(started, "finish_game")
    started.refresh_from_db()
    assert started.status == Game.Status.FINISHED
    assert started.finished_at is not None
    assert started.winner is None
    assert fresh(pending).status == PendingAction.Status.CANCELLED
    assert started.events.filter(kind="game_finished").exists()
    with pytest.raises(GameError, match="завершена"):
        act(started, masha, "roll")
    with pytest.raises(GameError, match="завершена"):
        host(started, "finish_game")


def test_finish_game_is_host_only(started, masha):
    with pytest.raises(GameError, match="только ведущий"):
        act(started, masha, "finish_game")


def test_finish_game_can_be_undone(started, masha):
    host(started, "pause")
    host(started, "finish_game")
    host(started, "undo")
    started.refresh_from_db()
    assert started.status == Game.Status.PAUSED
    assert started.finished_at is None


def test_finish_game_in_lobby(game, seeded):
    lobby.join_game(game, "Маша")
    host(game, "finish_game")
    assert fresh(game).status == Game.Status.FINISHED
    with pytest.raises(GameError, match="уже началась"):
        lobby.join_game(fresh(game), "Петя")


# --- Активы и колоды -------------------------------------------------------------------


def test_bought_asset_keeps_card_description(started, masha):
    card = stock_card(price=10)
    card.text = "Компания растёт."
    card.save()
    open_card(started, card)
    host(started, "buy", quantity=2)
    assert masha.assets.get().description == "Компания растёт."


def test_deck_rebuilt_after_cards_replaced(started, masha):
    """После make seed-reset старые id в колоде пропадают — колода собирается заново."""
    Card.objects.filter(category=CardCategory.DOODAD).delete()
    new = Card.objects.create(
        category=CardCategory.DOODAD,
        color="#000000",
        title="Новая трата",
        effect={"type": "expense", "amount": 500},
    )
    place(masha, cell_position(CellKind.DOODAD) - 1)
    act(started, masha, "roll", rnd=Dice(1))
    assert fresh(started).current_card == new
