"""Игровой движок: действия игроков и ведущего.

Все изменения игры идут через submit_action / decide. Каждое действие описано
в ACTIONS: кто может его делать, нужна ли санкция ведущего, проверка и исполнение.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from game import finance, snapshots
from game.errors import GameError
from game.events import log_event
from game.finance import (
    BANK_LOAN_RATE,
    BANK_LOAN_STEP,
    BANK_LOAN_TITLE,
    MAX_CHILDREN,
    loan_payment,
    receive,
    statement,
    take_bank_loan,
)
from game.models import (
    Asset,
    BoardCell,
    Card,
    CardCategory,
    CellKind,
    Game,
    Liability,
    LoanOffer,
    PendingAction,
    Player,
    Track,
)

rng = random.SystemRandom()

AUTO = "auto"
APPROVE = "approve"
HOST = "host"

CHARITY_TURNS = 3
DOWNSIZED_SKIP_TURNS = 2
FAST_TRACK_INCOME_MULTIPLIER = 100


@dataclass(frozen=True)
class Actor:
    """Кто действует: игрок или ведущий (player=None)."""

    player: Player | None = None

    @property
    def is_host(self):
        return self.player is None


HOST_ACTOR = Actor()


@dataclass
class Ctx:
    game: Game
    player: Player | None
    params: dict
    rnd: random.Random


@dataclass(frozen=True)
class Action:
    title: str
    policy: str  # AUTO, APPROVE или HOST
    run: Callable[[Ctx], None]
    check: Callable[[Ctx], None] = lambda ctx: None
    parse: Callable[[dict], dict] = lambda params: {}
    describe: Callable[[Ctx], str] = lambda ctx: ""
    # Для APPROVE: нужна ли санкция ведущего именно здесь (акции — без неё).
    needs_approval: Callable[[Ctx], bool] = lambda ctx: True
    current_only: bool = True  # только игрок, чей сейчас ход
    undoable: bool = True
    # Заявка теряет смысл, когда ход уходит дальше.
    phase_bound: bool = True
    phases: tuple = field(default=())


# --- Вход ------------------------------------------------------------------------------


def submit_action(game, actor, kind, params=None, rnd=None):
    """Игрок или ведущий выполняет действие (или отправляет заявку ведущему)."""
    action = ACTIONS.get(kind)
    if action is None:
        raise GameError("Неизвестное действие.")
    params = params or {}

    with transaction.atomic():
        game = _lock(game)
        _check_status(game, actor, action)
        player = _resolve_player(game, actor, action, params)
        ctx = Ctx(game, player, action.parse(params), rnd or rng)
        _check_phase(ctx, action)
        action.check(ctx)

        if action.policy == APPROVE and not actor.is_host and action.needs_approval(ctx):
            if game.pending_actions.filter(
                player=player, kind=kind, status=PendingAction.Status.PENDING
            ).exists():
                raise GameError("Такая заявка уже ждёт ведущего.")
            pending = PendingAction.objects.create(
                game=game,
                player=player,
                kind=kind,
                payload=ctx.params,
                description=action.describe(ctx),
            )
            log_event(
                game,
                "action_requested",
                player=player,
                action_id=pending.id,
                action=kind,
                text=f"{player.name} просит: {pending.description}",
            )
            return pending

        _execute(ctx, action)
        return None


def decide(game, action_id, approve, params=None, comment="", rnd=None):
    """Ведущий одобряет (можно с исправленными параметрами) или отклоняет заявку."""
    with transaction.atomic():
        game = _lock(game)
        pending = (
            game.pending_actions.select_related("player")
            .filter(id=action_id, status=PendingAction.Status.PENDING)
            .first()
        )
        if pending is None:
            raise GameError("Заявка не найдена или уже решена.")
        action = ACTIONS[pending.kind]
        pending.comment = comment[:300]
        pending.decided_at = timezone.now()

        if not approve:
            pending.status = PendingAction.Status.REJECTED
            pending.save()
            log_event(
                game,
                "action_rejected",
                player=pending.player,
                action_id=pending.id,
                text=_with_comment(f"Ведущий отклонил: {pending.description}", comment),
            )
            return pending

        ctx = Ctx(game, pending.player, action.parse(pending.payload | (params or {})), rnd or rng)
        if action.current_only and pending.player_id != _deciding_player_id(game):
            raise GameError("Ход уже перешёл к другому игроку.")
        _check_phase(ctx, action)
        action.check(ctx)
        pending.status = PendingAction.Status.APPROVED
        pending.payload = ctx.params
        pending.save()
        log_event(
            game,
            "action_approved",
            player=pending.player,
            action_id=pending.id,
            text=_with_comment(f"Ведущий одобрил: {action.describe(ctx)}", comment),
        )
        _execute(ctx, action)
        return pending


def cancel_request(game, player, action_id):
    with transaction.atomic():
        game = _lock(game)
        updated = game.pending_actions.filter(
            id=action_id, player=player, status=PendingAction.Status.PENDING
        ).update(status=PendingAction.Status.CANCELLED, decided_at=timezone.now())
        if not updated:
            raise GameError("Заявка не найдена или уже решена.")
        log_event(
            game,
            "action_cancelled",
            player=player,
            action_id=action_id,
            text=f"{player.name} отозвал(а) заявку",
        )


def _lock(game):
    return Game.objects.select_for_update().get(pk=game.pk)


def _with_comment(text, comment):
    return f"{text} ({comment})" if comment else text


def _check_status(game, actor, action):
    if game.status == Game.Status.LOBBY and action.run is not _run_finish:
        raise GameError("Игра ещё не началась.")
    if game.status == Game.Status.FINISHED and not (actor.is_host and action.run is _run_undo):
        raise GameError("Игра уже завершена.")
    if action.policy == HOST and not actor.is_host:
        raise GameError("Это может сделать только ведущий.")
    if game.status == Game.Status.PAUSED and not actor.is_host:
        raise GameError("Игра на паузе.")


def _resolve_player(game, actor, action, params):
    if not actor.is_host:
        # Перечитываем из БД: объект снаружи мог устареть (деньги изменились).
        player = game.players.filter(pk=actor.player.pk).first()
        if player is None:
            raise GameError("Вас нет в этой игре.")
    elif "player_id" in params:
        player = game.players.filter(id=parse_int(params["player_id"], "player_id")).first()
        if player is None:
            raise GameError("Игрок не найден.")
    else:
        # Ведущий действует за игрока, чей сейчас ход (или кому предложена сделка).
        player = game.players.filter(id=_deciding_player_id(game)).first()
    deciding = _deciding_player_id(game)
    if action.current_only and action.policy != HOST and getattr(player, "id", None) != deciding:
        raise GameError("Сейчас не ваш ход.")
    return player


def _deciding_player_id(game):
    """Кто сейчас решает: игрок, чей ход, или тот, кому по кругу предложили сделку."""
    return game.offer_player_id or game.current_player_id


def _check_phase(ctx, action):
    if action.phases and ctx.game.phase not in action.phases:
        raise GameError("Сейчас это сделать нельзя.")


def _execute(ctx, action):
    if action.undoable:
        snapshots.capture(ctx.game, action.title)
    action.run(ctx)


# --- Разбор параметров -----------------------------------------------------------------


def parse_int(value, name, minimum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise GameError(f"Неверное значение: {name}.") from None
    if isinstance(value, float) and value != number:
        raise GameError(f"Неверное значение: {name}.")
    if minimum is not None and number < minimum:
        raise GameError(f"Слишком маленькое значение: {name}.")
    return number


_money = finance.rub


# --- Поле и ходы -----------------------------------------------------------------------


def _cells(track):
    return list(BoardCell.objects.filter(track=track).order_by("position"))


def _set_phase(game, phase):
    game.phase = phase
    game.save(update_fields=["phase", "dice", "current_card"])


def _cancel_phase_bound(game):
    kinds = [kind for kind, a in ACTIONS.items() if a.phase_bound]
    game.pending_actions.filter(status=PendingAction.Status.PENDING, kind__in=kinds).update(
        status=PendingAction.Status.CANCELLED, decided_at=timezone.now()
    )


def _next_turn(game):
    _cancel_phase_bound(game)
    players = list(game.players.order_by("seat"))
    index = next(i for i, p in enumerate(players) if p.id == game.current_player_id)
    while True:
        index = (index + 1) % len(players)
        player = players[index]
        if player.skip_turns == 0:
            break
        player.skip_turns -= 1
        player.save(update_fields=["skip_turns"])
        log_event(game, "turn_skipped", player=player, text=f"{player.name} пропускает ход")

    game.current_player = player
    game.turn_number += 1
    game.paydays = 0  # ведущий мог передать ход, пока доход не получен
    game.offer_player = None
    game.stock_waiting = []
    game.dice = []
    game.current_card = None
    game.phase = Game.Phase.ROLL
    game.save()
    log_event(
        game,
        "turn_started",
        player=player,
        turn=game.turn_number,
        text=f"Ход {game.turn_number}: {player.name}",
    )


def _default_dice(player):
    """Сколько кубиков, если игрок не выбрал сам."""
    return 1 if player.track == Track.RAT_RACE else 2


def _move(ctx, steps):
    game, player = ctx.game, ctx.player
    cells = _cells(player.track)
    if not cells:
        raise GameError("Поле не заполнено — выполните make seed.")
    start = player.position
    passed = [cells[(start + i) % len(cells)] for i in range(1, steps + 1)]
    player.position = passed[-1].position
    player.save(update_fields=["position"])
    log_event(
        game,
        "moved",
        player=player,
        track=player.track,
        start=start,
        end=player.position,
        steps=steps,
        path=[c.position for c in passed],
    )

    income_kind = CellKind.PAYCHECK if player.track == Track.RAT_RACE else CellKind.CASHFLOW_DAY
    paydays = sum(cell.kind == income_kind for cell in passed)
    if paydays:
        # Доход игрок получает сам кнопкой «Получить», после этого срабатывает клетка.
        _announce_landing(game, player, passed[-1])
        game.paydays = paydays
        _set_phase(game, Game.Phase.INCOME)
        game.save(update_fields=["paydays"])
    else:
        _land(ctx, passed[-1])


def _income_amount(player):
    if player.track == Track.FAST_TRACK:
        return player.fast_track_income
    return statement(player).cashflow


def _run_collect_income(ctx):
    game, player = ctx.game, ctx.player
    for _ in range(game.paydays):
        _payday(game, player)
    game.paydays = 0
    game.save(update_fields=["paydays"])
    _land(ctx, _current_cell(ctx), announce=False)


def _payday(game, player):
    amount = _income_amount(player)
    if amount >= 0:
        receive(player, amount)
    else:
        pay(player, -amount, "отрицательный денежный поток")
    log_event(
        game,
        "payday",
        player=player,
        amount=amount,
        text=f"{player.name}: доход {_money(amount)}",
    )


def _announce_landing(game, player, cell):
    log_event(
        game,
        "landed",
        player=player,
        cell_id=cell.id,
        cell_kind=cell.kind,
        text=f"{player.name}: {cell.title}",
    )


def _land(ctx, cell, announce=True):
    game, player = ctx.game, ctx.player
    if announce:
        _announce_landing(game, player, cell)
    match cell.kind:
        case CellKind.OPPORTUNITY:
            _set_phase(game, Game.Phase.CHOOSE_DEAL)
        case CellKind.MARKET:
            _draw(ctx, CardCategory.MARKET)
            _set_phase(game, Game.Phase.CARD)
        case CellKind.DOODAD:
            # Игрок сам нажимает «Заплатить» — см. _run_pay_card.
            _draw(ctx, CardCategory.DOODAD)
            _set_phase(game, Game.Phase.PAY)
        case CellKind.CHARITY:
            _set_phase(game, Game.Phase.CHARITY)
        case CellKind.BABY:
            if player.children < MAX_CHILDREN:
                player.children += 1
                player.save(update_fields=["children"])
                log_event(
                    game,
                    "baby",
                    player=player,
                    children=player.children,
                    text=f"{player.name}: родился ребёнок!",
                )
            _set_phase(game, Game.Phase.END_TURN)
        case CellKind.DOWNSIZED:
            amount = statement(player).total_expenses
            pay(player, amount, "увольнение")
            player.skip_turns = DOWNSIZED_SKIP_TURNS
            player.save(update_fields=["skip_turns"])
            log_event(
                game,
                "downsized",
                player=player,
                amount=amount,
                text=f"{player.name} уволен(а): платит {_money(amount)} и пропускает 2 хода",
            )
            _set_phase(game, Game.Phase.END_TURN)
        case CellKind.BUSINESS:
            _set_phase(game, Game.Phase.BUSINESS)
        case CellKind.DREAM:
            _set_phase(game, Game.Phase.DREAM)
        case CellKind.LOSS:
            amount = player.cash // 2
            pay(player, amount, cell.title)
            log_event(
                game,
                "paid",
                player=player,
                amount=amount,
                text=f"{player.name} теряет {_money(amount)}: {cell.title}",
            )
            _set_phase(game, Game.Phase.END_TURN)
        case _:  # зарплата и день денежного потока уже начислены при проходе
            _set_phase(game, Game.Phase.END_TURN)


def _draw(ctx, category):
    game = ctx.game
    deck = game.decks.select_for_update().get(category=category)
    existing = set(Card.objects.filter(id__in=deck.card_ids).values_list("id", flat=True))
    for _ in range(2):
        while deck.next_index < len(deck.card_ids):
            card_id = deck.card_ids[deck.next_index]
            deck.next_index += 1
            if card_id in existing:
                deck.save()
                card = Card.objects.get(id=card_id)
                game.current_card = card
                game.save(update_fields=["current_card"])
                log_event(
                    game,
                    "card_drawn",
                    player=ctx.player,
                    card_id=card.id,
                    category=card.category,
                    text=f"{ctx.player.name} тянет карточку «{card.title}»",
                )
                return card
        # Колода кончилась — перемешиваем заново. Если её карточки удалили из админки
        # (например, make seed-reset), собираем колоду из тех, что есть сейчас.
        if not existing:
            deck.card_ids = list(
                Card.objects.filter(category=category, is_active=True).values_list("id", flat=True)
            )
            existing = set(deck.card_ids)
        ctx.rnd.shuffle(deck.card_ids)
        deck.next_index = 0
    raise GameError("Колода пуста.")


def _current_cell(ctx):
    """Клетка, на которой стоит игрок, чей сейчас ход (сделку могли предложить другому)."""
    player = ctx.player
    if player.id != ctx.game.current_player_id:
        player = ctx.game.players.get(id=ctx.game.current_player_id)
    return BoardCell.objects.get(track=player.track, position=player.position)


def pay(player, amount, reason):
    loan = finance.pay(player, amount)
    if loan:
        log_event(
            player.game,
            "auto_loan",
            player=player,
            amount=loan,
            text=f"{player.name}: не хватает денег ({reason}) — кредит {_money(loan)}",
        )


def _need_cash(player, amount):
    if amount > player.cash:
        raise GameError(f"Не хватает денег: нужно {_money(amount)}, есть {_money(player.cash)}.")


# --- Действия игрока -------------------------------------------------------------------


def _parse_roll(params):
    return {"dice": parse_int(params["dice"], "dice", 1)} if "dice" in params else {}


def _check_roll(ctx):
    options = ctx.player.dice_options()
    if ctx.params.get("dice", _default_dice(ctx.player)) not in options:
        if len(options) == 1:
            raise GameError(f"Сейчас можно бросить только {_dice_word(options[0])}.")
        raise GameError(f"Можно бросить {' или '.join(map(str, options))} кубика.")


def _dice_word(count):
    return "1 кубик" if count == 1 else f"{count} кубика"


def _run_roll(ctx):
    player = ctx.player
    count = ctx.params.get("dice", _default_dice(player))
    values = [ctx.rnd.randint(1, 6) for _ in range(count)]
    if player.charity_turns:
        player.charity_turns -= 1
        player.save(update_fields=["charity_turns"])
    ctx.game.dice = values
    ctx.game.save(update_fields=["dice"])
    log_event(
        ctx.game,
        "dice_rolled",
        player=player,
        values=values,
        text=f"{player.name} выбросил(а) {' + '.join(map(str, values))}"
        + (f" = {sum(values)}" if len(values) > 1 else ""),
    )
    _move(ctx, sum(values))


def _parse_deal(params):
    size = params.get("size")
    if size not in ("small", "big"):
        raise GameError("Выберите малую или крупную сделку.")
    return {"size": size}


def _run_choose_deal(ctx):
    category = CardCategory.SMALL_DEAL if ctx.params["size"] == "small" else CardCategory.BIG_DEAL
    card = _draw(ctx, category)
    _set_phase(ctx.game, Game.Phase.CARD)
    if card.effect.get("type") == "stock":
        _wait_for_stock_holders(ctx, card)


def _wait_for_stock_holders(ctx, card):
    """Акции на столе: у кого они есть, решают — продать по цене карточки или отказаться.
    Пока все не решат, вытянувший карточку не может закончить ход."""
    game, symbol = ctx.game, card.effect["symbol"]
    holders = [
        p
        for p in game.players.exclude(id=game.current_player_id).order_by("seat")
        if p.assets.filter(kind=Asset.Kind.STOCK, key=symbol, quantity__gt=0).exists()
    ]
    game.stock_waiting = [p.id for p in holders]
    game.save(update_fields=["stock_waiting"])
    if holders:
        names = ", ".join(p.name for p in holders)
        log_event(
            game,
            "stock_waiting",
            text=f"Акции {symbol} есть у: {names} — продают по {_money(card.effect['price'])} "
            "или отказываются",
        )


def _waiting_names(game):
    names = dict(game.players.filter(id__in=game.stock_waiting).values_list("id", "name"))
    return ", ".join(names[i] for i in game.stock_waiting if i in names)


def _stop_waiting(game, player):
    if player.id in game.stock_waiting:
        game.stock_waiting = [i for i in game.stock_waiting if i != player.id]
        game.save(update_fields=["stock_waiting"])


def _check_decline_sell(ctx):
    if ctx.player.id not in ctx.game.stock_waiting:
        raise GameError("От вас решения не ждут.")


def _run_decline_sell(ctx):
    _stop_waiting(ctx.game, ctx.player)
    log_event(
        ctx.game,
        "sell_declined",
        player=ctx.player,
        text=f"{ctx.player.name} не продаёт акции",
    )


def _check_end_turn(ctx):
    if ctx.game.stock_waiting:
        raise GameError(f"Ждём решения по акциям: {_waiting_names(ctx.game)}.")


def _deal_card(ctx):
    card = ctx.game.current_card
    if card is None or card.category not in (CardCategory.SMALL_DEAL, CardCategory.BIG_DEAL):
        raise GameError("Нет открытой сделки.")
    return card


def _parse_buy(params):
    return {"quantity": parse_int(params.get("quantity", 1), "quantity", 1)}


def _buy_price(ctx):
    effect = _deal_card(ctx).effect
    if effect.get("type") == "stock":
        return effect["price"] * ctx.params["quantity"]
    return effect.get("down_payment", 0)


def _check_buy(ctx):
    _need_cash(ctx.player, _buy_price(ctx))


def _describe_buy(ctx):
    card = _deal_card(ctx)
    if card.effect.get("type") == "stock":
        q = ctx.params["quantity"]
        return f"купить {q} акц. {card.effect['symbol']} за {_money(_buy_price(ctx))}"
    return f"купить «{card.title}», взнос {_money(_buy_price(ctx))}"


def _run_buy(ctx):
    game, player = ctx.game, ctx.player
    card = _deal_card(ctx)
    effect = card.effect
    price = _buy_price(ctx)
    player.cash -= price
    player.save(update_fields=["cash"])
    if effect.get("type") == "stock":
        Asset.objects.create(
            player=player,
            kind=Asset.Kind.STOCK,
            title=f"Акции {effect['symbol']}",
            key=effect["symbol"],
            description=card.text,
            quantity=ctx.params["quantity"],
            cost=effect["price"],
            source_card=card,
        )
    else:
        asset = Asset.objects.create(
            player=player,
            kind=Asset.Kind.REAL_ESTATE,
            title=effect.get("property", card.title),
            key=effect.get("property", ""),
            description=card.text,
            cost=effect.get("cost", 0),
            cashflow=effect.get("cashflow", 0),
            source_card=card,
        )
        if effect.get("mortgage"):
            Liability.objects.create(
                player=player,
                title=f"Ипотека: {asset.title}",
                balance=effect["mortgage"],
                payment=0,  # платёж уже учтён в денежном потоке объекта
                asset=asset,
            )
    log_event(
        game,
        "bought",
        player=player,
        card_id=card.id,
        amount=price,
        text=f"{player.name}: {_describe_buy(ctx)}",
    )
    _close_offer(game)
    _set_phase(game, Game.Phase.END_TURN)


def _parse_sell(params):
    return {
        "asset_id": parse_int(params.get("asset_id"), "asset_id"),
        "quantity": parse_int(params.get("quantity", 1), "quantity", 1),
    }


def _sell_offer(ctx):
    """(актив, выручка до погашения ипотеки, сумма ипотеки) по открытой карточке."""
    card = ctx.game.current_card
    if card is None:
        raise GameError("Нет открытой карточки.")
    effect = card.effect
    asset = ctx.player.assets.filter(id=ctx.params["asset_id"]).first()
    if asset is None:
        raise GameError("Актив не найден.")
    if effect.get("type") in ("stock", "stock_price"):
        if (
            effect["type"] == "stock"
            and ctx.player.id != ctx.game.current_player_id
            and ctx.player.id not in ctx.game.stock_waiting
        ):
            raise GameError("Продать акции можно, только пока от вас ждут решения.")
        if asset.kind != Asset.Kind.STOCK or asset.key != effect["symbol"]:
            raise GameError("Эта карточка не про эти акции.")
        if ctx.params["quantity"] > asset.quantity:
            raise GameError(f"У вас только {asset.quantity} акций.")
        return asset, effect["price"] * ctx.params["quantity"], 0
    if effect.get("type") == "sell_offer":
        if asset.kind != Asset.Kind.REAL_ESTATE or asset.key != effect["property"]:
            raise GameError(f"Покупатель ищет «{effect['property']}».")
        mortgage = asset.liability.balance if hasattr(asset, "liability") else 0
        return asset, effect["price"], mortgage
    raise GameError("По этой карточке ничего продать нельзя.")


def _describe_sell(ctx):
    asset, price, mortgage = _sell_offer(ctx)
    what = (
        f"{ctx.params['quantity']} акц. {asset.key}"
        if asset.kind == Asset.Kind.STOCK
        else (f"«{asset.title}»")
    )
    tail = f", минус ипотека {_money(mortgage)}" if mortgage else ""
    return f"продать {what} за {_money(price)}{tail}"


def _run_sell(ctx):
    player = ctx.player
    asset, price, mortgage = _sell_offer(ctx)
    text = f"{player.name}: {_describe_sell(ctx)}"
    net = price - mortgage
    if net >= 0:
        receive(player, net)
    else:
        pay(player, -net, "продажа в минус")
    if asset.kind == Asset.Kind.STOCK and ctx.params["quantity"] < asset.quantity:
        asset.quantity -= ctx.params["quantity"]
        asset.save(update_fields=["quantity"])
    else:
        asset.delete()  # ипотека удаляется вместе с объектом
    log_event(ctx.game, "sold", player=player, amount=net, text=text)
    _stop_waiting(ctx.game, player)


def _run_pay_card(ctx):
    """Оплата карточки трат. Не хватает наличных — автоматически берётся кредит."""
    game, player = ctx.game, ctx.player
    card = game.current_card
    amount = card.effect.get("amount", 0)
    pay(player, amount, card.title)
    log_event(
        game,
        "paid",
        player=player,
        amount=amount,
        text=f"{player.name} платит {_money(amount)}: {card.title}",
    )
    _set_phase(game, Game.Phase.END_TURN)


def _run_pass(ctx):
    game, player = ctx.game, ctx.player
    log_event(game, "passed", player=player, text=f"{player.name} отказывается")
    _cancel_phase_bound(game)
    candidates = _offer_candidates(ctx)
    if candidates:
        # От недвижимости или бизнеса отказались — предлагаем следующему по кругу.
        ids = [p.id for p in candidates]
        following = candidates[ids.index(player.id) + 1 :] if player.id in ids else candidates
        if following:
            game.offer_player = following[0]
            game.save(update_fields=["offer_player"])
            log_event(
                game,
                "offered",
                player=game.offer_player,
                text=f"Предложение «{_offer_title(ctx)}» переходит к {game.offer_player.name}",
            )
            return
        log_event(game, "offer_declined", text=f"Никто не купил «{_offer_title(ctx)}»")
    _close_offer(game)
    _set_phase(game, Game.Phase.END_TURN)


def _offer_candidates(ctx):
    """Кому по кругу предлагают сделку после отказа: остальные игроки того же круга,
    по порядку мест начиная со следующего за тем, чей ход. Пусто — сделка не передаётся."""
    game = ctx.game
    card = game.current_card
    if game.phase == Game.Phase.BUSINESS:
        track = Track.FAST_TRACK
    elif (
        game.phase == Game.Phase.CARD
        and card is not None
        and card.category in (CardCategory.SMALL_DEAL, CardCategory.BIG_DEAL)
        and card.effect.get("type") == "real_estate"
    ):
        track = Track.RAT_RACE
    else:
        return []
    players = list(game.players.order_by("seat"))
    index = next(i for i, p in enumerate(players) if p.id == game.current_player_id)
    following = players[index + 1 :] + players[:index]
    return [p for p in following if p.track == track]


def _offer_title(ctx):
    if ctx.game.phase == Game.Phase.BUSINESS:
        return _current_cell(ctx).title
    return ctx.game.current_card.title


def _close_offer(game):
    if game.offer_player_id:
        game.offer_player = None
        game.save(update_fields=["offer_player"])


def _charity_amount(ctx):
    if ctx.player.track == Track.FAST_TRACK:
        return _current_cell(ctx).effect.get("cost", 0)
    return statement(ctx.player).total_income // 10


def _check_charity(ctx):
    _need_cash(ctx.player, _charity_amount(ctx))


def _run_charity(ctx):
    player = ctx.player
    amount = _charity_amount(ctx)
    pay(player, amount, "благотворительность")
    if player.track == Track.FAST_TRACK:
        player.fast_track_charity = True
        bonus = "до конца игры можно бросать 1, 2 или 3 кубика"
    else:
        player.charity_turns = CHARITY_TURNS
        bonus = f"следующие {CHARITY_TURNS} хода можно бросать 1 или 2 кубика"
    player.save(update_fields=["charity_turns", "fast_track_charity"])
    log_event(
        ctx.game,
        "charity",
        player=player,
        amount=amount,
        text=f"{player.name} жертвует {_money(amount)}: {bonus}",
    )
    _set_phase(ctx.game, Game.Phase.END_TURN)


def _check_cell_purchase(ctx):
    _need_cash(ctx.player, _current_cell(ctx).effect.get("cost", 0))


def _run_buy_business(ctx):
    player = ctx.player
    cell = _current_cell(ctx)
    cost, flow = cell.effect.get("cost", 0), cell.effect.get("cashflow", 0)
    pay(player, cost, cell.title)
    Asset.objects.create(
        player=player,
        kind=Asset.Kind.BUSINESS,
        title=cell.title,
        description=cell.description,
        cost=cost,
        cashflow=flow,
    )
    player.fast_track_income += flow
    player.save(update_fields=["fast_track_income"])
    log_event(
        ctx.game,
        "bought",
        player=player,
        amount=cost,
        text=f"{player.name} покупает «{cell.title}» за {_money(cost)}: +{_money(flow)} в месяц",
    )
    _close_offer(ctx.game)
    _set_phase(ctx.game, Game.Phase.END_TURN)


def _run_buy_dream(ctx):
    game, player = ctx.game, ctx.player
    cell = _current_cell(ctx)
    pay(player, cell.effect.get("cost", 0), cell.title)
    game.winner = player
    game.status = Game.Status.FINISHED
    game.finished_at = timezone.now()
    game.save()
    log_event(
        game,
        "game_won",
        player=player,
        text=f"{player.name} покупает мечту «{cell.title}» и побеждает!",
    )


def _parse_amount(params):
    return {"amount": parse_int(params.get("amount"), "amount", 1)}


def _check_loan_step(amount):
    if amount % BANK_LOAN_STEP:
        raise GameError(f"Кредит берётся суммами, кратными {_money(BANK_LOAN_STEP)}.")


def _run_take_loan(ctx):
    amount = ctx.params["amount"]
    take_bank_loan(ctx.player, amount)
    log_event(
        ctx.game,
        "loan_taken",
        player=ctx.player,
        amount=amount,
        text=f"{ctx.player.name} берёт кредит {_money(amount)} "
        f"(+{_money(int(amount * BANK_LOAN_RATE))} к расходам)",
    )


def _parse_repay(params):
    return _parse_amount(params) | {
        "liability_id": parse_int(params.get("liability_id"), "liability")
    }


def _repay_target(ctx):
    liability = ctx.player.liabilities.filter(id=ctx.params["liability_id"]).first()
    if liability is None:
        raise GameError("Долг не найден.")
    if liability.asset_id:
        raise GameError("Ипотека на объект гасится при его продаже.")
    return liability


def _check_repay(ctx):
    liability = _repay_target(ctx)
    amount = ctx.params["amount"]
    if amount > liability.balance:
        raise GameError(f"Долг всего {_money(liability.balance)}.")
    if liability.lender_id:
        pass  # долг игроку можно гасить любой суммой
    elif liability.title == BANK_LOAN_TITLE:
        _check_loan_step(amount)
    elif amount != liability.balance:
        raise GameError("Этот долг гасится только целиком.")
    _need_cash(ctx.player, amount)


def _run_repay(ctx):
    liability = _repay_target(ctx)
    amount = ctx.params["amount"]
    ctx.player.cash -= amount
    ctx.player.save(update_fields=["cash"])
    liability.balance -= amount
    if liability.lender:
        receive(liability.lender, amount)
    if liability.balance == 0:
        liability.delete()
    else:
        liability.payment = (
            loan_payment(liability.balance, liability.rate)
            if liability.lender_id
            else int(liability.balance * BANK_LOAN_RATE)
        )
        liability.save()
    log_event(
        ctx.game,
        "loan_repaid",
        player=ctx.player,
        amount=amount,
        text=f"{ctx.player.name} гасит «{liability.title}» на {_money(amount)}",
    )


# --- Займы между игроками --------------------------------------------------------------

MAX_LOAN_RATE = 100


def _parse_offer_loan(params):
    return {
        "borrower_id": parse_int(params.get("borrower_id"), "borrower_id"),
        "amount": parse_int(params.get("amount"), "amount", 1),
        "rate": parse_int(params.get("rate", 0), "rate", 0),
    }


def _borrower(ctx):
    borrower = ctx.game.players.filter(id=ctx.params["borrower_id"]).first()
    if borrower is None:
        raise GameError("Игрок не найден.")
    if borrower.id == ctx.player.id:
        raise GameError("Нельзя дать в долг самому себе.")
    return borrower


def _check_offer_loan(ctx):
    _borrower(ctx)
    if ctx.params["rate"] > MAX_LOAN_RATE:
        raise GameError(f"Процент — от 0 до {MAX_LOAN_RATE} в месяц.")
    _need_cash(ctx.player, ctx.params["amount"])


def _loan_terms(amount, rate):
    payment = loan_payment(amount, rate)
    return f"{_money(amount)} под {rate}% в месяц (платёж {_money(payment)})"


def _run_offer_loan(ctx):
    lender, borrower = ctx.player, _borrower(ctx)
    amount, rate = ctx.params["amount"], ctx.params["rate"]
    LoanOffer.objects.filter(game=ctx.game, lender=lender, borrower=borrower).delete()
    LoanOffer.objects.create(
        game=ctx.game, lender=lender, borrower=borrower, amount=amount, rate=rate
    )
    log_event(
        ctx.game,
        "loan_offered",
        player=lender,
        text=f"{lender.name} предлагает {borrower.name} в долг {_loan_terms(amount, rate)}",
    )


def _parse_loan_offer(params):
    return {"offer_id": parse_int(params.get("offer_id"), "offer_id")}


def _loan_offer(ctx):
    offer = (
        LoanOffer.objects.select_related("lender", "borrower")
        .filter(game=ctx.game, id=ctx.params["offer_id"])
        .first()
    )
    if offer is None or ctx.player.id not in (offer.lender_id, offer.borrower_id):
        raise GameError("Предложение не найдено.")
    return offer


def _check_accept_loan(ctx):
    offer = _loan_offer(ctx)
    if offer.borrower_id != ctx.player.id:
        raise GameError("Принять заём может только тот, кому его предложили.")
    if offer.lender.cash < offer.amount:
        raise GameError(f"У {offer.lender.name} уже нет {_money(offer.amount)}.")


def _run_accept_loan(ctx):
    offer = _loan_offer(ctx)
    lender, borrower = offer.lender, ctx.player
    lender.cash -= offer.amount
    lender.save(update_fields=["cash"])
    receive(borrower, offer.amount)
    Liability.objects.create(
        player=borrower,
        lender=lender,
        rate=offer.rate,
        title=f"Долг игроку {lender.name}",
        balance=offer.amount,
        payment=loan_payment(offer.amount, offer.rate),
    )
    offer.delete()
    log_event(
        ctx.game,
        "loan_accepted",
        player=borrower,
        text=f"{borrower.name} берёт в долг у {lender.name} "
        f"{_loan_terms(offer.amount, offer.rate)}",
    )


def _run_decline_loan(ctx):
    offer = _loan_offer(ctx)
    offer.delete()
    if ctx.player.id == offer.borrower_id:
        text = f"{offer.borrower.name} отказывается от займа {offer.lender.name}"
    else:
        text = f"{offer.lender.name} отзывает предложение займа для {offer.borrower.name}"
    log_event(ctx.game, "loan_declined", player=ctx.player, text=text)


def _check_fast_track(ctx):
    player, game = ctx.player, ctx.game
    if player.track != Track.RAT_RACE:
        raise GameError(f"{player.name} уже в большом круге.")
    if not statement(player).can_exit_rat_race:
        raise GameError(f"{player.name}: пассивный доход ещё не превышает расходы.")
    if player == game.current_player and game.phase not in (Game.Phase.ROLL, Game.Phase.END_TURN):
        raise GameError(f"Дождитесь, пока {player.name} закончит ход.")


def _run_fast_track(ctx):
    player = ctx.player
    player.fast_track_income = statement(player).passive_income * FAST_TRACK_INCOME_MULTIPLIER
    player.track = Track.FAST_TRACK
    player.position = 0
    player.charity_turns = 0
    player.save()
    log_event(
        ctx.game,
        "fast_track",
        player=player,
        text=f"{player.name} переходит в большой круг! "
        f"Доход дня денежного потока: {_money(player.fast_track_income)}",
    )


def _run_end_turn(ctx):
    _next_turn(ctx.game)


# --- Действия ведущего -----------------------------------------------------------------


def _run_pause(ctx):
    if ctx.game.status != Game.Status.RUNNING:
        raise GameError("Игра уже на паузе.")
    ctx.game.status = Game.Status.PAUSED
    ctx.game.save(update_fields=["status"])
    log_event(ctx.game, "paused", text="Ведущий заморозил игру")


def _run_resume(ctx):
    if ctx.game.status != Game.Status.PAUSED:
        raise GameError("Игра не на паузе.")
    ctx.game.status = Game.Status.RUNNING
    ctx.game.save(update_fields=["status"])
    log_event(ctx.game, "resumed", text="Игра продолжается")


def _parse_adjust(params):
    amount = parse_int(params.get("amount"), "amount")
    if amount == 0:
        raise GameError("Сумма не может быть нулевой.")
    return {"amount": amount, "reason": str(params.get("reason", ""))[:200]}


def _run_adjust_cash(ctx):
    player, amount = ctx.player, ctx.params["amount"]
    player.cash += amount
    player.save(update_fields=["cash"])
    sign = "+" if amount > 0 else "−"
    log_event(
        ctx.game,
        "cash_adjusted",
        player=player,
        amount=amount,
        text=_with_comment(
            f"Ведущий: {player.name} {sign}{_money(abs(amount))}", ctx.params["reason"]
        ),
    )


def _run_finish(ctx):
    game = ctx.game
    game.pending_actions.filter(status=PendingAction.Status.PENDING).update(
        status=PendingAction.Status.CANCELLED, decided_at=timezone.now()
    )
    game.status = Game.Status.FINISHED
    game.finished_at = timezone.now()
    game.save(update_fields=["status", "finished_at"])
    log_event(game, "game_finished", text="Ведущий завершил игру")


def _run_undo(ctx):
    label = snapshots.restore_latest(ctx.game)
    if label is None:
        raise GameError("Нечего отменять.")
    ctx.game.pending_actions.filter(status=PendingAction.Status.PENDING).update(
        status=PendingAction.Status.CANCELLED, decided_at=timezone.now()
    )
    log_event(ctx.game, "undone", text=f"Ведущий отменил действие: {label}")


P = Game.Phase
CARD_OPEN = (P.CARD, P.END_TURN)  # продавать можно, пока карточка лежит на столе

ACTIONS = {
    "roll": Action(
        "Бросок", AUTO, _run_roll, _check_roll, _parse_roll, phases=(P.ROLL,), phase_bound=False
    ),
    "choose_deal": Action(
        "Выбор сделки", AUTO, _run_choose_deal, parse=_parse_deal, phases=(P.CHOOSE_DEAL,)
    ),
    "buy": Action(
        "Покупка", AUTO, _run_buy, _check_buy, _parse_buy, _describe_buy, phases=(P.CARD,)
    ),
    "sell": Action(
        "Продажа",
        APPROVE,
        _run_sell,
        lambda ctx: _sell_offer(ctx),
        _parse_sell,
        _describe_sell,
        needs_approval=lambda ctx: _sell_offer(ctx)[0].kind != Asset.Kind.STOCK,
        current_only=False,
        phases=CARD_OPEN,
    ),
    "collect_income": Action("Доход", AUTO, _run_collect_income, phases=(P.INCOME,)),
    "pay_card": Action("Оплата", AUTO, _run_pay_card, phases=(P.PAY,)),
    "pass": Action(
        "Отказ", AUTO, _run_pass, phases=(P.CHOOSE_DEAL, P.CARD, P.CHARITY, P.BUSINESS, P.DREAM)
    ),
    "charity": Action(
        "Благотворительность",
        APPROVE,
        _run_charity,
        _check_charity,
        describe=lambda ctx: f"пожертвовать {_money(_charity_amount(ctx))}",
        phases=(P.CHARITY,),
    ),
    "buy_business": Action(
        "Покупка бизнеса",
        AUTO,
        _run_buy_business,
        _check_cell_purchase,
        describe=lambda ctx: f"купить «{_current_cell(ctx).title}»",
        phases=(P.BUSINESS,),
    ),
    "buy_dream": Action(
        "Покупка мечты",
        APPROVE,
        _run_buy_dream,
        _check_cell_purchase,
        describe=lambda ctx: f"купить мечту «{_current_cell(ctx).title}»",
        phases=(P.DREAM,),
    ),
    "offer_loan": Action(
        "Предложение займа",
        AUTO,
        _run_offer_loan,
        _check_offer_loan,
        _parse_offer_loan,
        current_only=False,
        undoable=False,
        phase_bound=False,
    ),
    "accept_loan": Action(
        "Заём у игрока",
        AUTO,
        _run_accept_loan,
        _check_accept_loan,
        _parse_loan_offer,
        current_only=False,
        phase_bound=False,
    ),
    "decline_loan": Action(
        "Отказ от займа",
        AUTO,
        _run_decline_loan,
        lambda ctx: _loan_offer(ctx),
        _parse_loan_offer,
        current_only=False,
        undoable=False,
        phase_bound=False,
    ),
    "take_loan": Action(
        "Кредит",
        APPROVE,
        _run_take_loan,
        lambda ctx: _check_loan_step(ctx.params["amount"]),
        _parse_amount,
        lambda ctx: f"взять кредит {_money(ctx.params['amount'])}",
        current_only=False,
        phase_bound=False,
    ),
    "repay_loan": Action(
        "Погашение долга",
        APPROVE,
        _run_repay,
        _check_repay,
        _parse_repay,
        lambda ctx: f"погасить «{_repay_target(ctx).title}» на {_money(ctx.params['amount'])}",
        # Долг игроку гасят напрямую, без ведущего.
        needs_approval=lambda ctx: _repay_target(ctx).lender_id is None,
        current_only=False,
        phase_bound=False,
    ),
    "decline_sell": Action(
        "Отказ от продажи",
        AUTO,
        _run_decline_sell,
        _check_decline_sell,
        current_only=False,
        phases=CARD_OPEN,
    ),
    "end_turn": Action(
        "Конец хода", AUTO, _run_end_turn, _check_end_turn, phases=(P.END_TURN,), phase_bound=False
    ),
    # Только ведущий
    "pause": Action("Пауза", HOST, _run_pause, undoable=False, phase_bound=False),
    "resume": Action("Продолжение", HOST, _run_resume, undoable=False, phase_bound=False),
    "adjust_cash": Action(
        "Корректировка денег", HOST, _run_adjust_cash, parse=_parse_adjust, phase_bound=False
    ),
    "next_turn": Action("Передача хода", HOST, _run_end_turn, phase_bound=False),
    # Игрок говорит ведущему «Я хочу выйти в большой круг», программа проверяет условие,
    # а переводит ведущий. Автоматического перехода нет.
    "go_fast_track": Action(
        "Перевод в большой круг", HOST, _run_fast_track, _check_fast_track, phase_bound=False
    ),
    # Отмена возвращает завершённую игру, если ведущий нажал по ошибке.
    "finish_game": Action("Завершение игры", HOST, _run_finish, phase_bound=False),
    "undo": Action("Отмена", HOST, _run_undo, undoable=False, phase_bound=False),
}
