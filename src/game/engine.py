"""Utils for running the game."""

from src.proto.gem_proto import GemType
from src.game import gem_utils


def is_gems_taken_only_gold(player_action):
    gems = player_action.gems_taken
    gold_gem_count = gems[GemType.GOLD]
    return (gem_utils.AllZerosExcept(gems, GemType.GOLD) and
            (gold_gem_count == 0 or gold_gem_count == 1))


def is_reserved_revealed_card(player_action):
    return (is_gems_taken_only_gold(player_action) and
            player_action.purchased_card_id is None and
            player_action.reserved_card_id is not None and
            player_action.topdeck_level is None and
            player_action.noble_tile_id is None)


def is_reserved_top_deck(player_action):
    return (is_gems_taken_only_gold(player_action) and
            player_action.purchased_card_id is None and
            player_action.reserved_card_id is None and
            player_action.topdeck_level is not None and
            player_action.noble_tile_id is None)


def is_purchased_card(player_action):
    return (gem_utils.NumGems(player_action.gems_taken) == 0 and
            player_action.purchased_card_id is not None and
            player_action.reserved_card_id is None and
            player_action.topdeck_level is None)


def is_taking_different_gems(player_action):
    gems_taken = player_action.gems_taken
    gem_types = gem_utils.GetNonEmptyGemTypes(gems_taken)
    if len(gem_types) > 3:
        return False
    if not all(gems_taken[gem_type] == 1 for gem_type in gem_types):
        return False
    return (player_action.purchased_card_id is None and
            player_action.reserved_card_id is None and
            player_action.topdeck_level is None and
            player_action.noble_tile_id is None)


def is_double_taking_gems(player_action):
    gems_taken = player_action.gems_taken
    gem_types = gem_utils.GetNonEmptyGemTypes(gems_taken)
    if len(gem_types) != 1:
        return False
    return (player_action.gems_taken[gem_types[0]] == 2 and
            player_action.purchased_card_id is None and
            player_action.reserved_card_id is None and
            player_action.topdeck_level is None and
            player_action.noble_tile_id is None)


def check_player_action(player_game_state, player_action):
    # Gems taken must be avaliable.
    gems_taken = player_action.gems_taken
    gem_utils.VerifyNonNegativeGems(gems_taken)
    gems_available = player_game_state.gem_counts
    if not gem_utils.CanTakeFrom(gems_available, gems_taken):
        raise ValueError("Not enough gems left")

    # Must have enough gems to return.
    self_gems = player_game_state.self_state.gem_counts
    gems_returned = player_action.gems_returned
    gem_utils.VerifyNonNegativeGems(gems_returned)
    if not gem_utils.CanTakeFrom(self_gems, gems_returned):
        raise ValueError("Not enough gems of type " + str(gem_type) + " to return")

    # Must return exactly down to limit.
    num_gems_taken = gem_utils.NumGems(gems_taken)
    excess_gems = num_gems_taken - player_game_state.GemLimit()
    num_gems_returned = gem_utils.NumGems(gems_returned)
    if excess_gems <= 0 and num_gems_returned > 0:
        raise ValueError("Cannot return gems under limit")
    if excess_gems > 0 and (excess_gems - num_gems_returned != 0):
        raise ValueError("Must return gems back to the limit exactly")

    if is_reserved_revealed_card(player_action):
        # Must not exceed reserve limit.
        if not player_game_state.CanReserve():
            raise ValueError("Can't reserve any more cards")
        # Reserved card must exist.
        card = player_game_state.GetRevealedCardById(
            player_action.reserved_card_id)
        if card is None:
            raise ValueError("Card with asset_id=" + player_action.reserved_card_id
                             + " does not exist")
    elif is_reserved_top_deck(player_action):
        # Must not exceed reserve limit.
        if not player_game_state.CanReserve():
            raise ValueError("Can't reserve any more cards")
        # Reserved card must exist.
        if not player_game_state.CanTopDeck(player_action.topdeck_level):
            raise ValueError("No more cards in deck " + str(player_action.topdeck_level))
    elif is_purchased_card(player_action):
        # Card must exist.
        card = player_game_state.GetReservedOrRevealedCardById(
            player_action.purchased_card_id)
        if card is None:
            raise ValueError("Card with asset_id=" + player_action.reserved_card_id
                             + " does not exist")
        discounted_cost = gem_utils.GetDiscountedCost(
            card.cost, player_game_state.self_state.gem_discounts)
        if not gem_utils.ExactlyPaysFor(discounted_cost,
                                        player_action.gems_returned):
            raise ValueError("Did not exactly pay for card.")
    elif is_taking_different_gems(player_action):
        if (num_gems_taken < 3 and
            gem_utils.NumNonGoldGems(gems_available) != num_gems_taken):
            raise ValueError("Cannot take less than 3 gems")
    elif is_double_taking_gems(player_action):
        gem_types = gem_utils.GetNonEmptyGemTypes(gems_taken)
        if len(gem_types) != 1 or player_game_state.CanTakeTwo(gem_types[0]):
            raise ValueError("Not enough " + str(gem_type) + " gems to take two")
    else:
        raise ValueError("PlayerAction malformed:\n" + str(player_action))

    # Obtaining a noble
    if player_action.noble_tile_id is not None:
        noble_tile = player_game_state.GetNobleById(player_action.noble_tile_id)
        if noble_tile is None:
            raise ValueError("Noble with asset_id=" + player_action.noble_tile_id
                             + " does not exist")
        costs = player_action.noble_tile.gem_type_requirements
        for gem_type in costs:
            if costs[gem_type] > player_game_state.self_state.gem_discounts[gem_type]:
                raise ValueError("Don't have the cards to obtain noble tile")
    # Everything checks out.
    return
