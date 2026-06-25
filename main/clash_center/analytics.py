"""Read-only analytics from stored Clash Center battle data."""
import math
from collections import defaultdict

from django.conf import settings
from django.db.models import Q

from main.clash_center.api_client import ClashRoyaleClient
from main.clash_center.tiers import RANKED_TIERS, tier_label
from main.models import ClashBattle, ClashCard, ClashPlayer

MIN_DECK_BATTLES = 5
MIN_CARD_BATTLES_WIN_RATE = 15
MIN_MY_DECK_BATTLES = 3
TOP_N = 15
TOP_CARDS_N = 10
RECOMMEND_N = 5


def owner_tag() -> str:
    return ClashRoyaleClient.normalize_tag(
        getattr(settings, 'CLASH_CENTER_PLAYER_TAG', '') or ''
    )


def _card_lookup() -> dict[int, ClashCard]:
    return {c.card_id: c for c in ClashCard.objects.all()}


def _deck_key(cards: list) -> tuple:
    return tuple(sorted(int(c) for c in cards))


def _win_score(wins: int, battles: int) -> float:
    if battles <= 0:
        return 0.0
    return (wins / battles) * math.sqrt(battles)


def _cards_for_battle(battle: ClashBattle, tag: str) -> tuple[list, bool]:
    """Return (deck cards, won) from the perspective of tag."""
    tag = ClashRoyaleClient.normalize_tag(tag)
    if ClashRoyaleClient.normalize_tag(battle.player_tag) == tag:
        return battle.player_cards, battle.player_won
    if ClashRoyaleClient.normalize_tag(battle.opponent_tag) == tag:
        return battle.opponent_cards, not battle.player_won
    return [], False


def _deck_cards_display(deck: tuple, cards: dict[int, ClashCard]) -> list[dict]:
    rows = []
    for card_id in deck:
        card = cards.get(card_id)
        rows.append({
            'card_id': card_id,
            'name': card.name if card else f'Card {card_id}',
            'elixir': card.elixir if card else 0,
            'icon_url': card.icon_url if card else '',
        })
    return rows


def my_battles_qs():
    tag = owner_tag()
    if not tag or tag == '#':
        return ClashBattle.objects.none()
    return ClashBattle.objects.filter(
        Q(player_tag=tag) | Q(opponent_tag=tag)
    )


def my_deck_stats(tier: int | None = None) -> list[dict]:
    battles = my_battles_qs()
    if tier in RANKED_TIERS:
        battles = battles.filter(tier=tier)

    tag = owner_tag()
    stats: dict[tuple, dict] = defaultdict(lambda: {'uses': 0, 'wins': 0})
    for battle in battles.iterator():
        deck, won = _cards_for_battle(battle, tag)
        key = _deck_key(deck)
        if len(key) < 8:
            continue
        stats[key]['uses'] += 1
        if won:
            stats[key]['wins'] += 1

    cards = _card_lookup()
    rows = []
    min_battles = MIN_MY_DECK_BATTLES if tier else MIN_DECK_BATTLES
    for deck, data in stats.items():
        if data['uses'] < min_battles:
            continue
        deck_cards = _deck_cards_display(deck, cards)
        rows.append({
            'cards': deck_cards,
            'uses': data['uses'],
            'wins': data['wins'],
            'win_rate': round(100 * data['wins'] / data['uses'], 1),
            'avg_elixir': round(sum(c['elixir'] for c in deck_cards) / 8, 1),
            'score': _win_score(data['wins'], data['uses']),
        })
    rows.sort(key=lambda r: (-r['uses'], -r['score']))
    return rows[:TOP_N]


def _card_stats_for_tier(tier: int) -> dict:
    battles = ClashBattle.objects.filter(tier=tier).only('player_cards', 'player_won')
    stats: dict[int, dict] = defaultdict(lambda: {'uses': 0, 'wins': 0})

    for battle in battles.iterator():
        for card_id in battle.player_cards:
            cid = int(card_id)
            stats[cid]['uses'] += 1
            if battle.player_won:
                stats[cid]['wins'] += 1

    cards = _card_lookup()
    total_battles = battles.count() or 1
    all_rows = []
    for card_id, data in stats.items():
        card = cards.get(card_id)
        all_rows.append({
            'card_id': card_id,
            'name': card.name if card else f'Card {card_id}',
            'elixir': card.elixir if card else 0,
            'icon_url': card.icon_url if card else '',
            'uses': data['uses'],
            'wins': data['wins'],
            'win_rate': round(100 * data['wins'] / data['uses'], 1),
            'usage_rate': round(100 * data['uses'] / total_battles, 1),
        })

    by_usage = sorted(all_rows, key=lambda r: (-r['usage_rate'], -r['win_rate']))
    qualified = [r for r in all_rows if r['uses'] >= MIN_CARD_BATTLES_WIN_RATE]
    by_win_rate = sorted(qualified, key=lambda r: (-r['win_rate'], -r['uses']))

    return {
        'by_usage': by_usage[:TOP_CARDS_N],
        'by_win_rate': by_win_rate[:TOP_CARDS_N],
        'all': by_usage,
    }


def _deck_stats_for_tier(tier: int) -> list[dict]:
    battles = ClashBattle.objects.filter(tier=tier).only('player_cards', 'player_won')
    stats: dict[tuple, dict] = defaultdict(lambda: {'uses': 0, 'wins': 0})

    for battle in battles.iterator():
        key = _deck_key(battle.player_cards)
        if len(key) < 8:
            continue
        stats[key]['uses'] += 1
        if battle.player_won:
            stats[key]['wins'] += 1

    cards = _card_lookup()
    rows = []
    for deck, data in stats.items():
        if data['uses'] < MIN_DECK_BATTLES:
            continue
        deck_cards = _deck_cards_display(deck, cards)
        rows.append({
            'cards': deck_cards,
            'uses': data['uses'],
            'wins': data['wins'],
            'win_rate': round(100 * data['wins'] / data['uses'], 1),
            'avg_elixir': round(sum(c['elixir'] for c in deck_cards) / 8, 1),
            'score': _win_score(data['wins'], data['uses']),
        })
    rows.sort(key=lambda r: (-r['score'], -r['uses']))
    return rows[:TOP_N]


def _deck_swap_suggestions(my_deck: tuple, tier: int, top_cards: list[dict]) -> list[dict]:
    """Suggest card swaps for one of the owner's decks based on tier meta."""
    if not top_cards:
        return []

    cards = _card_lookup()
    meta_by_id = {c['card_id']: c for c in top_cards}
    my_set = set(my_deck)
    suggestions = []

    for card_id, meta in meta_by_id.items():
        if card_id in my_set:
            continue
        for out_id in my_deck:
            out_card = cards.get(out_id)
            out_wr = meta_by_id[out_id]['win_rate'] if out_id in meta_by_id else 40
            if meta['win_rate'] > out_wr + 3 and meta['usage_rate'] > 8:
                suggestions.append({
                    'swap_out': out_id,
                    'swap_in': card_id,
                    'swap_out_name': out_card.name if out_card else f'Card {out_id}',
                    'swap_in_name': meta['name'],
                    'reason': (
                        f'Swap {out_card.name if out_card else out_id} for {meta["name"]} — '
                        f'{meta["win_rate"]}% WR, {meta["usage_rate"]}% usage in this league'
                    ),
                })
                break

    suggestions.sort(key=lambda s: meta_by_id.get(s['swap_in'], {}).get('usage_rate', 0), reverse=True)
    return suggestions[:3]


def _recommend_decks(
    tier: int,
    top_decks: list[dict],
    top_cards: list[dict],
    my_decks: list[dict],
) -> list[dict]:
    if not top_decks:
        return []

    cards = _card_lookup()
    battles = ClashBattle.objects.filter(tier=tier).only(
        'player_cards', 'opponent_cards', 'player_won'
    )

    opponent_usage: dict[tuple, int] = defaultdict(int)
    for battle in battles.iterator():
        key = _deck_key(battle.opponent_cards)
        if len(key) == 8:
            opponent_usage[key] += 1
    meta_opponent_keys = {k for k, _ in sorted(opponent_usage.items(), key=lambda x: -x[1])[:5]}

    matchup_stats: dict[tuple, dict] = defaultdict(lambda: {'uses': 0, 'wins': 0})
    for battle in battles.iterator():
        opp_key = _deck_key(battle.opponent_cards)
        if opp_key not in meta_opponent_keys:
            continue
        our_key = _deck_key(battle.player_cards)
        if len(our_key) < 8:
            continue
        matchup_stats[our_key]['uses'] += 1
        if battle.player_won:
            matchup_stats[our_key]['wins'] += 1

    top_card_ids = {c['card_id'] for c in top_cards[:5]}
    my_deck_keys = {tuple(c['card_id'] for c in d['cards']) for d in my_decks}
    candidates = []
    seen_decks = set()

    def _append(deck_key, reason: str, score: float, uses: int, wins: int, swaps=None):
        if deck_key in seen_decks or len(deck_key) < 8:
            return
        seen_decks.add(deck_key)
        deck_cards = _deck_cards_display(deck_key, cards)
        candidates.append({
            'cards': deck_cards,
            'reason': reason,
            'uses': uses,
            'wins': wins,
            'win_rate': round(100 * wins / uses, 1) if uses else 0,
            'avg_elixir': round(sum(c['elixir'] for c in deck_cards) / 8, 1),
            'score': score,
            'swaps': swaps or [],
            'is_my_deck': deck_key in my_deck_keys,
        })

    for deck in my_decks[:3]:
        key = tuple(c['card_id'] for c in deck['cards'])
        swaps = _deck_swap_suggestions(key, tier, top_cards)
        if swaps:
            _append(
                key,
                'Suggested tweaks to your deck for this league meta',
                deck['score'],
                deck['uses'],
                deck['wins'],
                swaps=swaps,
            )

    for deck in top_decks[:8]:
        key = tuple(c['card_id'] for c in deck['cards'])
        _append(key, 'Strong overall win rate in this league', deck['score'], deck['uses'], deck['wins'])

    for deck_key, data in sorted(
        matchup_stats.items(),
        key=lambda x: _win_score(x[1]['wins'], x[1]['uses']),
        reverse=True,
    ):
        if data['uses'] < 5:
            continue
        _append(
            deck_key,
            'Counters popular meta decks in this league',
            _win_score(data['wins'], data['uses']),
            data['uses'],
            data['wins'],
        )

    for deck in top_decks:
        key = tuple(c['card_id'] for c in deck['cards'])
        overlap = len(set(key) & top_card_ids)
        if overlap >= 2 and deck['win_rate'] >= 52:
            _append(
                key,
                f'Uses {overlap} of the top meta cards in this league',
                deck['score'] * (1 + 0.1 * overlap),
                deck['uses'],
                deck['wins'],
            )

    candidates.sort(key=lambda c: -c['score'])
    return candidates[:RECOMMEND_N]


def my_summary() -> dict:
    battles = my_battles_qs()
    count = battles.count()
    tag = owner_tag()
    wins = 0
    for battle in battles.iterator():
        _, won = _cards_for_battle(battle, tag)
        if won:
            wins += 1

    tier = 0
    if tag and tag != '#':
        player = ClashPlayer.objects.filter(tag=tag).first()
        if player and player.tier in RANKED_TIERS:
            tier = player.tier
        elif count:
            latest = battles.order_by('-battle_time').first()
            if latest:
                tier = latest.tier

    return {
        'tag': tag,
        'battle_count': count,
        'overall_win_rate': round(100 * wins / count, 1) if count else 0,
        'tier': tier,
        'tier_label': tier_label(tier) if tier else 'Unknown',
        'decks': my_deck_stats(),
    }


def tier_summary(tier: int) -> dict:
    battles_qs = ClashBattle.objects.filter(tier=tier)
    battle_count = battles_qs.count()
    wins = battles_qs.filter(player_won=True).count()
    card_stats = _card_stats_for_tier(tier) if battle_count else {
        'by_usage': [], 'by_win_rate': [], 'all': [],
    }
    top_decks = _deck_stats_for_tier(tier) if battle_count else []
    my_decks = my_deck_stats(tier=tier)
    recommendations = (
        _recommend_decks(tier, top_decks, card_stats['all'], my_decks) if battle_count else []
    )

    return {
        'tier': tier,
        'label': tier_label(tier),
        'battle_count': battle_count,
        'overall_win_rate': round(100 * wins / battle_count, 1) if battle_count else 0,
        'cards_by_usage': card_stats['by_usage'],
        'cards_by_win_rate': card_stats['by_win_rate'],
        'all_cards': card_stats['all'],
        'top_decks': top_decks,
        'my_decks': my_decks,
        'recommendations': recommendations,
    }


def build_clash_center_context(selected_tier: int | None = None) -> dict:
    from main.clash_center.sync_state import (
        get_last_sync_summary,
        get_sync_state,
        next_sync_at,
        refresh_collection_status,
        sync_interval_hours,
        sync_status_label,
    )

    running, progress = refresh_collection_status()
    state = get_sync_state()
    my = my_summary()

    if selected_tier in RANKED_TIERS:
        tier = selected_tier
    elif my['tier'] in RANKED_TIERS:
        tier = my['tier']
    else:
        tier = 7

    tiers_nav = []
    for t in RANKED_TIERS:
        count = ClashBattle.objects.filter(tier=t).count()
        tiers_nav.append({'tier': t, 'label': tier_label(t), 'battle_count': count})

    return {
        'my_data': my,
        'selected_tier': tier,
        'tier_data': tier_summary(tier),
        'tiers_nav': tiers_nav,
        'total_battles': ClashBattle.objects.count(),
        'total_players': ClashPlayer.objects.count(),
        'total_cards': ClashCard.objects.count(),
        'scrape_running': running,
        'scrape_message': progress.get('message', ''),
        'sync_status': sync_status_label(),
        'sync_interval_hours': sync_interval_hours(),
        'last_sync_at': state.last_sync_at,
        'next_sync_at': next_sync_at(),
        'last_summary': get_last_sync_summary(),
    }
