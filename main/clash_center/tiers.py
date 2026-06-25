"""Ranked ladder tiers (leagueNumber 1–7 from the Royale API).

Order is lowest → highest skill (2025+ Ranked Mode):
Master I through Ultimate Champion. Challenger leagues were removed.
"""

RANKED_TIERS: dict[int, str] = {
    1: 'Master I',
    2: 'Master II',
    3: 'Master III',
    4: 'Champion',
    5: 'Grand Champion',
    6: 'Royal Champion',
    7: 'Ultimate Champion',
}

TIER_CHOICES = [(k, v) for k, v in RANKED_TIERS.items()]


def tier_label(tier: int) -> str:
    return RANKED_TIERS.get(tier, f'Tier {tier}')
