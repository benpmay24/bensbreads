"""Tool implementations for the Clash Center AI agent (read-only DB access)."""
import json

from django.conf import settings
from django.db.models import Q

from main.clash_center.analytics import (
    MIN_TOP_DECK_BATTLES,
    _card_stats_for_tier,
    _deck_stats_for_tier,
    _significant_win_rate,
    my_deck_stats,
    my_summary,
    owner_tag,
    tier_summary,
)
from main.clash_center.api_client import ClashRoyaleClient
from main.clash_center.tiers import RANKED_TIERS, tier_label
from main.models import ClashBattle, ClashCard, ClashPlayer

MAX_BATTLES_RETURN = 50
MAX_CARDS_RETURN = 30
MAX_CATALOG_RETURN = 200


def _card_to_dict(card: ClashCard) -> dict:
    return {
        'card_id': card.card_id,
        'name': card.name,
        'elixir': card.elixir,
        'rarity': card.rarity,
        'max_level': card.max_level,
        'max_evolution_level': card.max_evolution_level,
        'has_evolution': card.max_evolution_level > 0,
    }


def _card_names(card_ids: list) -> list[str]:
    lookup = {c.card_id: c.name for c in ClashCard.objects.filter(card_id__in=card_ids)}
    return [lookup.get(int(cid), f'Card {cid}') for cid in card_ids]


def _battle_row(battle: ClashBattle) -> dict:
    return {
        'battle_time': battle.battle_time.isoformat(),
        'tier': battle.tier,
        'league': tier_label(battle.tier),
        'player_tag': battle.player_tag,
        'opponent_tag': battle.opponent_tag,
        'player_won': battle.player_won,
        'player_crowns': battle.player_crowns,
        'opponent_crowns': battle.opponent_crowns,
        'player_cards': _card_names(battle.player_cards),
        'opponent_cards': _card_names(battle.opponent_cards),
        'game_mode': battle.game_mode,
    }


def tool_get_database_summary(_input: dict) -> dict:
    tag = owner_tag()
    state_battles = ClashBattle.objects.count()
    return {
        'owner_tag': tag,
        'total_battles': state_battles,
        'total_players': ClashPlayer.objects.count(),
        'total_cards_in_catalog': ClashCard.objects.count(),
        'battles_by_league': {
            tier_label(t): ClashBattle.objects.filter(tier=t).count()
            for t in RANKED_TIERS
        },
        'owner_battles': ClashBattle.objects.filter(
            Q(player_tag=tag) | Q(opponent_tag=tag)
        ).count() if tag and tag != '#' else 0,
    }


def tool_get_my_performance(_input: dict) -> dict:
    return my_summary()


def tool_get_my_recent_deck(_input: dict) -> dict:
    """Most recent battle deck and most-used deck for the configured player."""
    tag = owner_tag()
    if not tag or tag == '#':
        return {'error': 'CLASH_CENTER_PLAYER_TAG not configured'}

    result = {'owner_tag': tag}

    battle = (
        ClashBattle.objects.filter(Q(player_tag=tag) | Q(opponent_tag=tag))
        .order_by('-battle_time')
        .first()
    )
    if battle:
        is_player = battle.player_tag == tag
        cards = _card_names(battle.player_cards if is_player else battle.opponent_cards)
        result['most_recent_battle'] = {
            'deck': cards,
            'battle_time': battle.battle_time.isoformat(),
            'league': tier_label(battle.tier),
            'won': battle.player_won if is_player else not battle.player_won,
            'crowns': (
                battle.player_crowns if is_player else battle.opponent_crowns
            ),
        }

    decks = my_deck_stats()
    if decks:
        top = decks[0]
        result['most_used_deck'] = {
            'deck': [c['name'] for c in top['cards']],
            'uses': top['uses'],
            'wins': top['wins'],
            'win_rate': top['win_rate'],
            'avg_elixir': top['avg_elixir'],
        }

    if 'most_recent_battle' not in result and 'most_used_deck' not in result:
        return {'error': 'No battles found for your tag in the database'}
    return result


def tool_get_my_decks(input: dict) -> dict:
    tier = input.get('tier')
    if tier is not None and tier != '':
        try:
            tier = int(tier)
        except (TypeError, ValueError):
            tier = None
    if tier is not None and tier not in RANKED_TIERS:
        return {'error': f'tier must be 1-7, got {tier}'}
    decks = my_deck_stats(tier=tier)
    slim = []
    for d in decks:
        slim.append({
            'win_rate': d['win_rate'],
            'ci_low': d['ci_low'],
            'ci_high': d['ci_high'],
            'uses': d['uses'],
            'wins': d['wins'],
            'avg_elixir': d['avg_elixir'],
            'sig_advantage': d['sig_advantage'],
            'sig_disadvantage': d['sig_disadvantage'],
            'p_value_greater': d['p_value_greater'],
            'cards': [c['name'] for c in d['cards']],
        })
    return {'tier': tier, 'decks': slim}


def tool_get_league_meta(input: dict) -> dict:
    tier = int(input['tier'])
    if tier not in RANKED_TIERS:
        return {'error': f'tier must be 1-7, got {tier}'}
    data = tier_summary(tier)
    return {
        'tier': tier,
        'league': data['label'],
        'battle_count': data['battle_count'],
        'league_avg_win_rate': data['overall_win_rate'],
        'baseline_wr': data['baseline_wr'],
        'top_cards_by_usage': [
            {k: c[k] for k in ('name', 'usage_rate', 'win_rate', 'ci_low', 'ci_high', 'uses', 'sig_advantage')}
            for c in data['cards_by_usage'][:10]
        ],
        'top_cards_by_win_rate_significant': [
            {k: c[k] for k in ('name', 'win_rate', 'ci_low', 'ci_high', 'uses', 'p_value_greater')}
            for c in data['cards_by_win_rate'][:10]
        ],
        'top_decks_significant': [
            {
                'win_rate': d['win_rate'],
                'ci_low': d['ci_low'],
                'ci_high': d['ci_high'],
                'uses': d['uses'],
                'cards': [c['name'] for c in d['cards']],
            }
            for d in data['top_decks'][:10]
        ],
        'my_decks_in_league': [
            {
                'win_rate': d['win_rate'],
                'uses': d['uses'],
                'cards': [c['name'] for c in d['cards']],
            }
            for d in data['my_decks'][:5]
        ],
    }


def tool_get_top_cards(input: dict) -> dict:
    tier = int(input['tier'])
    if tier not in RANKED_TIERS:
        return {'error': f'tier must be 1-7'}
    stats = _card_stats_for_tier(tier)
    sort = (input.get('sort') or 'usage').lower()
    limit = min(int(input.get('limit', 15)), MAX_CARDS_RETURN)
    significant_only = bool(input.get('significant_only', False))

    if sort == 'win_rate':
        rows = stats['by_win_rate']
    else:
        rows = stats['by_usage']

    if significant_only:
        rows = [r for r in stats['all'] if _significant_win_rate(r)]

    return {
        'league': tier_label(tier),
        'baseline_wr': stats['baseline_wr'],
        'cards': [
            {
                'name': r['name'],
                'elixir': r['elixir'],
                'usage_rate': r['usage_rate'],
                'win_rate': r['win_rate'],
                'ci_low': r['ci_low'],
                'ci_high': r['ci_high'],
                'uses': r['uses'],
                'sig_advantage': r['sig_advantage'],
                'p_value_greater': r['p_value_greater'],
            }
            for r in rows[:limit]
        ],
    }


def tool_get_top_decks(input: dict) -> dict:
    tier = int(input['tier'])
    if tier not in RANKED_TIERS:
        return {'error': f'tier must be 1-7'}
    top_decks, _ = _deck_stats_for_tier(tier)
    limit = min(int(input.get('limit', 15)), MAX_CARDS_RETURN)
    return {
        'league': tier_label(tier),
        'min_battles': MIN_TOP_DECK_BATTLES,
        'note': 'Decks require 20+ battles and p<0.05 vs league baseline',
        'decks': [
            {
                'win_rate': d['win_rate'],
                'ci_low': d['ci_low'],
                'ci_high': d['ci_high'],
                'uses': d['uses'],
                'wins': d['wins'],
                'avg_elixir': d['avg_elixir'],
                'cards': [c['name'] for c in d['cards']],
            }
            for d in top_decks[:limit]
        ],
    }


def tool_get_recent_battles(input: dict) -> dict:
    qs = ClashBattle.objects.all().order_by('-battle_time')
    tag = owner_tag()

    if input.get('mine_only'):
        if tag and tag != '#':
            qs = qs.filter(Q(player_tag=tag) | Q(opponent_tag=tag))
    if input.get('player_tag'):
        t = ClashRoyaleClient.normalize_tag(input['player_tag'])
        qs = qs.filter(Q(player_tag=t) | Q(opponent_tag=t))
    if input.get('tier') is not None:
        tier = int(input['tier'])
        if tier in RANKED_TIERS:
            qs = qs.filter(tier=tier)

    limit = min(int(input.get('limit', 20)), MAX_BATTLES_RETURN)
    return {
        'count': qs.count(),
        'returned': min(limit, qs.count()),
        'battles': [_battle_row(b) for b in qs[:limit]],
    }


def tool_list_card_catalog(input: dict) -> dict:
    """Full card catalog with elixir, rarity, and evolution info."""
    qs = ClashCard.objects.all().order_by('elixir', 'name')

    if input.get('name_contains'):
        qs = qs.filter(name__icontains=input['name_contains'].strip())
    if input.get('rarity'):
        qs = qs.filter(rarity__iexact=input['rarity'].strip())
    if input.get('elixir') is not None:
        qs = qs.filter(elixir=int(input['elixir']))
    if input.get('has_evolution'):
        qs = qs.filter(max_evolution_level__gt=0)

    total = qs.count()
    if input.get('list_all'):
        limit = total
    else:
        limit = min(int(input.get('limit', MAX_CATALOG_RETURN)), MAX_CATALOG_RETURN)

    cards = [_card_to_dict(c) for c in qs[:limit]]
    return {
        'total_in_catalog': ClashCard.objects.count(),
        'matching': total,
        'returned': len(cards),
        'cards': cards,
    }


def tool_lookup_cards(input: dict) -> dict:
    qs = ClashCard.objects.all()
    if input.get('card_ids'):
        ids = [int(x) for x in input['card_ids']]
        qs = qs.filter(card_id__in=ids)
    elif input.get('name_contains'):
        qs = qs.filter(name__icontains=input['name_contains'].strip())
    else:
        return {'error': 'Provide card_ids or name_contains'}

    limit = min(int(input.get('limit', 20)), MAX_CARDS_RETURN)
    return {
        'cards': [_card_to_dict(c) for c in qs[:limit]],
    }


def tool_get_card_performance(input: dict) -> dict:
    """Win rate for specific cards in a league."""
    tier = int(input['tier'])
    if tier not in RANKED_TIERS:
        return {'error': 'tier must be 1-7'}

    names = input.get('card_names') or []
    if not names:
        return {'error': 'card_names required'}

    name_set = {n.lower() for n in names}
    card_ids = {
        c.card_id: c.name
        for c in ClashCard.objects.all()
        if c.name.lower() in name_set
    }
    if not card_ids:
        return {'error': 'No matching cards in catalog', 'searched': names}

    stats = _card_stats_for_tier(tier)
    by_id = {r['card_id']: r for r in stats['all']}
    results = []
    for cid, name in card_ids.items():
        row = by_id.get(cid)
        if row:
            results.append({
                'name': name,
                'win_rate': row['win_rate'],
                'ci_low': row['ci_low'],
                'ci_high': row['ci_high'],
                'usage_rate': row['usage_rate'],
                'uses': row['uses'],
                'sig_advantage': row['sig_advantage'],
                'p_value_greater': row['p_value_greater'],
            })
        else:
            results.append({'name': name, 'uses': 0, 'note': 'No appearances in this league'})

    return {'league': tier_label(tier), 'baseline_wr': stats['baseline_wr'], 'cards': results}


def tool_compare_deck_to_meta(input: dict) -> dict:
    """Compare a list of card names to top meta decks/cards in a league."""
    tier = int(input['tier'])
    card_names = input.get('card_names') or []
    if tier not in RANKED_TIERS:
        return {'error': 'tier must be 1-7'}

    id_by_name = {c.name.lower(): c.card_id for c in ClashCard.objects.all()}
    deck_ids = tuple(sorted(
        id_by_name[n.lower()] for n in card_names if n.lower() in id_by_name
    ))
    if len(deck_ids) < 8:
        return {'error': 'Need 8 recognized card names', 'found': len(deck_ids)}

    meta = tier_summary(tier)
    top_decks, all_decks = _deck_stats_for_tier(tier)
    my_row = next(
        (d for d in all_decks if tuple(c['card_id'] for c in d['cards']) == deck_ids),
        None,
    )

    overlap_scores = []
    for d in top_decks[:5]:
        their = {c['name'] for c in d['cards']}
        overlap = len(their & set(card_names))
        overlap_scores.append({
            'overlap_cards': overlap,
            'their_win_rate': d['win_rate'],
            'their_uses': d['uses'],
            'their_deck': [c['name'] for c in d['cards']],
        })

    missing_meta = []
    my_set = set(card_names)
    for c in meta['cards_by_win_rate']:
        if c['name'] in my_set:
            continue
        if c.get('sig_advantage') and c.get('usage_rate', 0) >= 8:
            missing_meta.append({
                'card': c['name'],
                'win_rate': c['win_rate'],
                'usage_rate': c['usage_rate'],
                'ci': f"{c['ci_low']}–{c['ci_high']}%",
            })
    missing_meta = missing_meta[:5]

    return {
        'your_deck': list(card_names),
        'your_stats_in_league': {
            'win_rate': my_row['win_rate'],
            'uses': my_row['uses'],
            'ci_low': my_row['ci_low'],
            'ci_high': my_row['ci_high'],
        } if my_row else None,
        'overlap_with_top_meta_decks': overlap_scores,
        'meta_cards_you_are_missing': missing_meta[:5],
    }


TOOL_DEFINITIONS = [
    {
        'name': 'get_database_summary',
        'description': 'Overview of all collected battle data: totals, battles per league, owner tag.',
        'input_schema': {'type': 'object', 'properties': {}, 'required': []},
    },
    {
        'name': 'get_my_performance',
        'description': 'Your overall ranked stats: battles, win rate, CI, current league.',
        'input_schema': {'type': 'object', 'properties': {}, 'required': []},
    },
    {
        'name': 'get_my_recent_deck',
        'description': (
            'Get your most recent battle deck and your most-used deck from stored battle logs. '
            'Use this when the user asks about their current, latest, or most recently used deck.'
        ),
        'input_schema': {'type': 'object', 'properties': {}, 'required': []},
    },
    {
        'name': 'get_my_decks',
        'description': (
            'Your most-used decks with win rates and statistical metrics. '
            'Omit tier to get all leagues — do NOT loop through every tier.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'tier': {'type': 'integer', 'description': 'Optional league 1-7; omit for all leagues'},
            },
            'required': [],
        },
    },
    {
        'name': 'get_league_meta',
        'description': 'Full meta snapshot for a league: top cards, top significant decks, your decks in that league.',
        'input_schema': {
            'type': 'object',
            'properties': {'tier': {'type': 'integer', 'description': 'League 1-7'}},
            'required': ['tier'],
        },
    },
    {
        'name': 'get_top_cards',
        'description': 'Top cards in a league by usage or win rate. Can filter to statistically significant only.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'tier': {'type': 'integer'},
                'sort': {'type': 'string', 'enum': ['usage', 'win_rate']},
                'significant_only': {'type': 'boolean'},
                'limit': {'type': 'integer'},
            },
            'required': ['tier'],
        },
    },
    {
        'name': 'get_top_decks',
        'description': 'Top win-rate decks in a league (20+ battles, p<0.05 significant).',
        'input_schema': {
            'type': 'object',
            'properties': {
                'tier': {'type': 'integer'},
                'limit': {'type': 'integer'},
            },
            'required': ['tier'],
        },
    },
    {
        'name': 'get_recent_battles',
        'description': (
            'Recent battles with decks and results. Set mine_only=true for your battles only. '
            'Use limit=1 for your latest battle.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'limit': {'type': 'integer'},
                'tier': {'type': 'integer'},
                'player_tag': {'type': 'string'},
                'mine_only': {'type': 'boolean'},
            },
            'required': [],
        },
    },
    {
        'name': 'list_card_catalog',
        'description': (
            'Browse the full Clash Royale card catalog: names, elixir costs, rarity, '
            'max level, and evolution availability. Use list_all=true for every card, '
            'or filter by name, rarity, elixir, or has_evolution.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'list_all': {'type': 'boolean', 'description': 'Return entire catalog (up to 200 cards)'},
                'name_contains': {'type': 'string'},
                'rarity': {'type': 'string', 'enum': ['common', 'rare', 'epic', 'legendary', 'champion']},
                'elixir': {'type': 'integer'},
                'has_evolution': {'type': 'boolean'},
                'limit': {'type': 'integer'},
            },
            'required': [],
        },
    },
    {
        'name': 'lookup_cards',
        'description': 'Look up specific cards by ID or name substring.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'card_ids': {'type': 'array', 'items': {'type': 'integer'}},
                'name_contains': {'type': 'string'},
                'limit': {'type': 'integer'},
            },
            'required': [],
        },
    },
    {
        'name': 'get_card_performance',
        'description': 'Win rate and significance for specific card names in a league.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'tier': {'type': 'integer'},
                'card_names': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['tier', 'card_names'],
        },
    },
    {
        'name': 'compare_deck_to_meta',
        'description': 'Compare an 8-card deck (by name) to the current league meta.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'tier': {'type': 'integer'},
                'card_names': {'type': 'array', 'items': {'type': 'string'}},
            },
            'required': ['tier', 'card_names'],
        },
    },
]

_TOOL_HANDLERS = {
    'get_database_summary': tool_get_database_summary,
    'get_my_performance': tool_get_my_performance,
    'get_my_recent_deck': tool_get_my_recent_deck,
    'get_my_decks': tool_get_my_decks,
    'get_league_meta': tool_get_league_meta,
    'get_top_cards': tool_get_top_cards,
    'get_top_decks': tool_get_top_decks,
    'get_recent_battles': tool_get_recent_battles,
    'list_card_catalog': tool_list_card_catalog,
    'lookup_cards': tool_lookup_cards,
    'get_card_performance': tool_get_card_performance,
    'compare_deck_to_meta': tool_compare_deck_to_meta,
}


def execute_tool(name: str, tool_input: dict) -> str:
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({'error': f'Unknown tool: {name}'})
    try:
        result = handler(tool_input or {})
        return json.dumps(result, default=str)
    except Exception as exc:
        return json.dumps({'error': str(exc)})
