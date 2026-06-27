"""Collect ranked battle data from the Royale API into the database."""
import hashlib
import logging
from collections import deque
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.clash_center.api_client import ClashRoyaleAPIError, ClashRoyaleClient
from main.clash_center.sync_state import release_lock, set_progress, try_acquire_lock
from main.clash_center.tiers import RANKED_TIERS
from main.models import ClashBattle, ClashCard, ClashCenterSyncState, ClashPlayer

logger = logging.getLogger(__name__)

RANKED_BATTLE_TYPES = {'pathoflegend'}
CARDS_STALE_HOURS = 24


def owner_tag() -> str:
    return ClashRoyaleClient.normalize_tag(
        getattr(settings, 'CLASH_CENTER_PLAYER_TAG', '') or ''
    )


def _card_icon_url(card: dict) -> str:
    icons = card.get('iconUrls') or {}
    return icons.get('medium', '') or icons.get('evolutionMedium', '')


def _extract_card_id(card: dict) -> int | None:
    card_id = card.get('id')
    return int(card_id) if card_id is not None else None


def _deck_from_member(member: dict) -> list[int]:
    cards = []
    for card in member.get('cards') or []:
        card_id = _extract_card_id(card)
        if card_id is not None:
            cards.append(card_id)
    return sorted(cards)


def _member_tier(member: dict) -> int:
    pol = member.get('pathOfLegendRank') or member.get('pathOfLegendTotals') or {}
    league = pol.get('leagueNumber') or member.get('leagueNumber')
    if league and 1 <= int(league) <= 7:
        return int(league)
    return 0


def _player_tier_from_profile(player: dict) -> int:
    for key in (
        'currentPathOfLegendSeasonResult',
        'lastPathOfLegendSeasonResult',
        'bestPathOfLegendSeasonResult',
    ):
        result = player.get(key) or {}
        league = result.get('leagueNumber')
        if league and 1 <= int(league) <= 7:
            return int(league)

    ls = player.get('leagueStatistics') or {}
    for season_key in ('currentSeason', 'previousSeason', 'bestSeason'):
        season = ls.get(season_key) or {}
        for rank_key in ('bestPathOfLegendRank', 'currentPathOfLegendRank'):
            pol = season.get(rank_key) or {}
            league = pol.get('leagueNumber')
            if league and 1 <= int(league) <= 7:
                return int(league)
    return 0


def _battle_tier(battle: dict, fallback_tier: int = 0) -> int:
    for side in ('team', 'opponent'):
        for member in battle.get(side) or []:
            tier = _member_tier(member)
            if tier in RANKED_TIERS:
                return tier
    season = battle.get('pathOfLegendSeasonResult') or {}
    league = season.get('leagueNumber')
    if league and 1 <= int(league) <= 7:
        return int(league)
    return fallback_tier


def _parse_battle_time(value: str):
    if not value:
        return None
    normalized = value.replace('.000Z', '+00:00').replace('Z', '+00:00')
    if 'T' in normalized and '+' not in normalized[10:]:
        normalized = normalized + '+00:00'
    try:
        return parse_datetime(normalized)
    except (ValueError, TypeError):
        return None


def _battle_uid(
    battle_time_raw: str,
    tag_a: str,
    tag_b: str,
    cards_a: list[int],
    cards_b: list[int],
) -> str:
    tags = tuple(sorted([tag_a.upper(), tag_b.upper()]))
    decks = tuple(sorted([tuple(cards_a), tuple(cards_b)]))
    raw = f'{battle_time_raw}|{tags}|{decks}'
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _battle_extra(battle: dict) -> dict:
    keys = (
        'type', 'battleTime', 'isLadderTournament', 'arena', 'gameMode',
        'deckSelection', 'isHostedMatch', 'leagueNumber',
    )
    return {k: battle[k] for k in keys if k in battle}


def sync_cards(client: ClashRoyaleClient, state: ClashCenterSyncState, force: bool = False) -> int:
    if not force and state.last_cards_sync_at:
        if timezone.now() - state.last_cards_sync_at < timedelta(hours=CARDS_STALE_HOURS):
            return 0

    set_progress('Syncing card catalog…')
    items = client.get_cards()
    created = 0
    for card in items:
        card_id = _extract_card_id(card)
        if card_id is None:
            continue
        _, was_created = ClashCard.objects.update_or_create(
            card_id=card_id,
            defaults={
                'name': card.get('name', f'Card {card_id}'),
                'elixir': int(card.get('elixirCost') or 0),
                'rarity': card.get('rarity', ''),
                'card_type': card.get('type', ''),
                'max_level': int(card.get('maxLevel') or 0),
                'max_evolution_level': int(card.get('maxEvolutionLevel') or 0),
                'icon_url': _card_icon_url(card),
            },
        )
        if was_created:
            created += 1
    state.last_cards_sync_at = timezone.now()
    state.save(update_fields=['last_cards_sync_at'])
    return created


def _upsert_player(tag: str, name: str = '', tier: int = 0) -> ClashPlayer:
    tag = ClashRoyaleClient.normalize_tag(tag)
    player, _ = ClashPlayer.objects.get_or_create(tag=tag)
    updates = []
    if name and player.name != name:
        player.name = name
        updates.append('name')
    if tier in RANKED_TIERS and player.tier != tier:
        player.tier = tier
        updates.append('tier')
    if updates:
        player.save(update_fields=updates + ['updated_at'])
    return player


def _parse_ranked_battles(
    battles: list[dict],
    log_owner_tag: str,
    fallback_tier: int,
) -> tuple[list[ClashBattle], list[str]]:
    """Parse battlelog entries; return new battle rows and opponent tags to explore."""
    parsed: list[ClashBattle] = []
    opponent_tags: list[str] = []
    log_owner_tag = ClashRoyaleClient.normalize_tag(log_owner_tag)

    for battle in battles:
        battle_type = (battle.get('type') or '').strip().lower()
        if battle_type not in RANKED_BATTLE_TYPES:
            continue

        battle_time_raw = battle.get('battleTime', '')
        battle_time = _parse_battle_time(battle_time_raw)
        if not battle_time:
            continue

        team = battle.get('team') or []
        opponent = battle.get('opponent') or []
        if not team or not opponent:
            continue

        player_side = team[0]
        opponent_side = opponent[0]
        player_tag = ClashRoyaleClient.normalize_tag(player_side.get('tag') or log_owner_tag)
        opponent_tag = ClashRoyaleClient.normalize_tag(opponent_side.get('tag') or '')
        if not opponent_tag:
            continue

        player_cards = _deck_from_member(player_side)
        opponent_cards = _deck_from_member(opponent_side)
        if len(player_cards) < 8 or len(opponent_cards) < 8:
            continue

        tier = _battle_tier(battle, fallback_tier)
        if tier not in RANKED_TIERS:
            continue

        player_crowns = int(player_side.get('crowns') or 0)
        opponent_crowns = int(opponent_side.get('crowns') or 0)
        arena = battle.get('arena') or {}
        game_mode = battle.get('gameMode') or {}

        parsed.append(ClashBattle(
            battle_uid=_battle_uid(battle_time_raw, player_tag, opponent_tag, player_cards, opponent_cards),
            battle_time=battle_time,
            tier=tier,
            player_tag=player_tag,
            opponent_tag=opponent_tag,
            player_won=player_crowns > opponent_crowns,
            player_cards=player_cards,
            opponent_cards=opponent_cards,
            player_crowns=player_crowns,
            opponent_crowns=opponent_crowns,
            arena_id=arena.get('id'),
            game_mode=game_mode.get('name', '') or str(game_mode.get('id', '')),
            raw_data=_battle_extra(battle),
        ))
        opponent_tags.append(opponent_tag)

    return parsed, opponent_tags


def collect_battles(client: ClashRoyaleClient, start_tag: str, max_battles: int) -> dict:
    """
    BFS through player battle logs starting at start_tag.
    Stops after recording up to max_battles new battles.
    """
    start_tag = ClashRoyaleClient.normalize_tag(start_tag)
    queue: deque[str] = deque([start_tag])
    visited_players: set[str] = set()
    battles_added = 0
    battles_seen = 0
    players_checked = 0

    while queue and battles_added < max_battles:
        tag = queue.popleft()
        if tag in visited_players:
            continue
        visited_players.add(tag)

        fallback_tier = 0
        display_name = tag
        try:
            profile = client.get_player(tag)
            fallback_tier = _player_tier_from_profile(profile)
            display_name = profile.get('name') or tag
            _upsert_player(tag, name=display_name, tier=fallback_tier)
        except ClashRoyaleAPIError as exc:
            logger.warning('Player profile failed for %s: %s', tag, exc)
            _upsert_player(tag)

        set_progress(
            f'Fetching battles for {display_name}…',
            current=players_checked + 1,
            total=len(visited_players) + len(queue),
        )

        try:
            battles = client.get_battlelog(tag)
        except ClashRoyaleAPIError as exc:
            logger.warning('Battle log failed for %s: %s', tag, exc)
            players_checked += 1
            continue

        players_checked += 1
        new_rows, opponent_tags = _parse_ranked_battles(battles, tag, fallback_tier)
        battles_seen += len(new_rows)

        if new_rows:
            created = ClashBattle.objects.bulk_create(new_rows, ignore_conflicts=True)
            battles_added += len(created)

        ClashPlayer.objects.filter(tag=tag).update(last_battle_fetch_at=timezone.now())

        for opp_tag in opponent_tags:
            opp_tag = ClashRoyaleClient.normalize_tag(opp_tag)
            if opp_tag not in visited_players:
                queue.append(opp_tag)

        if battles_added >= max_battles:
            break

    return {
        'players_checked': players_checked,
        'battles_added': battles_added,
        'battles_seen': battles_seen,
        'players_visited': len(visited_players),
    }


def run_collection(*, force: bool = False, skip_if_due: bool = True) -> dict:
    """Main entry point for the cron job."""
    from main.clash_center.sync_state import is_sync_due

    if skip_if_due and not force and not is_sync_due():
        return {'skipped': True, 'reason': 'not_due'}

    state = try_acquire_lock()
    if state is None:
        return {'skipped': True, 'reason': 'already_running'}

    client = ClashRoyaleClient()
    if not client.configured():
        release_lock(state, {'error': 'API not configured'})
        return {'error': 'CLASH_ROYALE_API_TOKEN is required'}

    my_tag = owner_tag()
    if not my_tag or my_tag == '#':
        release_lock(state, {'error': 'CLASH_CENTER_PLAYER_TAG is required'})
        return {'error': 'CLASH_CENTER_PLAYER_TAG is required'}

    max_battles = int(getattr(settings, 'CLASH_CENTER_MAX_BATTLES_PER_SYNC', 500))

    summary: dict = {'owner_tag': my_tag}
    try:
        summary['cards_new'] = sync_cards(client, state, force=force)
        battle_totals = collect_battles(client, my_tag, max_battles)
        summary.update(battle_totals)
        summary['total_battles'] = ClashBattle.objects.count()
        summary['total_players'] = ClashPlayer.objects.count()
        release_lock(state, summary)
        return summary
    except Exception as exc:
        logger.exception('Clash Center sync failed')
        summary['error'] = str(exc)
        release_lock(state, summary)
        return summary
