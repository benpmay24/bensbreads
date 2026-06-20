"""Geocode facility addresses for map placement."""
import hashlib
import logging
import time
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

GEOCODE_CACHE_PREFIX = 'dog_watch_geocode:'
GEOCODE_CACHE_TTL = 60 * 60 * 24 * 90  # 90 days

STATE_NAME_TO_ABBR = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
}


def normalize_state(state: str) -> str:
    """Return a two-letter state code when possible."""
    value = (state or '').strip()
    if not value:
        return ''
    if len(value) == 2:
        return value.upper()
    return STATE_NAME_TO_ABBR.get(value.lower(), value[:2].upper())


def _cache_key(city: str, state: str, zip_code: str = '', street: str = '') -> str:
    raw = '|'.join([
        (street or '').strip().lower(),
        (city or '').strip().lower(),
        normalize_state(state),
        (zip_code or '').strip()[:5],
    ])
    return hashlib.md5(raw.encode()).hexdigest()


def _lookup_cache(city: str, state: str, zip_code: str = '', street: str = '') -> tuple[Decimal, Decimal] | None:
    cached = cache.get(f'{GEOCODE_CACHE_PREFIX}{_cache_key(city, state, zip_code, street)}')
    if not cached:
        return None
    return Decimal(cached[0]), Decimal(cached[1])


def _store_cache(
    city: str, state: str, zip_code: str, lat: Decimal, lng: Decimal, street: str = '',
) -> None:
    payload = [str(lat), str(lng)]
    cache.set(
        f'{GEOCODE_CACHE_PREFIX}{_cache_key(city, state, zip_code, street)}',
        payload,
        GEOCODE_CACHE_TTL,
    )


def _request_geocode(query: str) -> tuple[Decimal, Decimal] | None:
    api_key = getattr(settings, 'GOOGLE_PLACES_API_KEY', '')
    if api_key:
        try:
            res = requests.get(
                'https://maps.googleapis.com/maps/api/geocode/json',
                params={'address': query, 'key': api_key},
                timeout=15,
            )
            data = res.json()
            if data.get('results'):
                loc = data['results'][0]['geometry']['location']
                return (
                    Decimal(str(round(loc['lat'], 6))),
                    Decimal(str(round(loc['lng'], 6))),
                )
            if data.get('status') not in ('ZERO_RESULTS', 'OK'):
                logger.warning('Google geocoding status %s for %s', data.get('status'), query)
        except requests.RequestException as exc:
            logger.warning('Google geocoding failed for %s: %s', query, exc)

    try:
        time.sleep(1.1)
        res = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'us'},
            headers={'User-Agent': "Ben's Breads Dog Watch (bensbreads.com)"},
            timeout=15,
        )
        results = res.json()
        if results:
            return (
                Decimal(str(round(float(results[0]['lat']), 6))),
                Decimal(str(round(float(results[0]['lon']), 6))),
            )
    except requests.RequestException as exc:
        logger.warning('Nominatim geocoding failed for %s: %s', query, exc)
    return None


def geocode(
    name: str,
    city: str,
    state: str,
    street: str = '',
    zip_code: str = '',
) -> tuple[Decimal | None, Decimal | None, bool]:
    """
    Return (latitude, longitude, geocoded) for a facility address.

    Results are cached by city/state/zip so import and sync stay fast.
    """
    state_abbr = normalize_state(state)
    if not city or not state_abbr:
        return None, None, False

    cached = _lookup_cache(city, state_abbr, zip_code, street)
    if cached:
        return cached[0], cached[1], True

    query_parts = [p for p in [street, city, state_abbr, zip_code, 'USA'] if p]
    coords = _request_geocode(', '.join(query_parts))

    if coords is None and street and zip_code:
        coords = _request_geocode(', '.join([street, zip_code, 'USA']))

    if coords is None and zip_code:
        coords = _request_geocode(', '.join([city, state_abbr, zip_code, 'USA']))

    if coords is None and (street or zip_code):
        coords = _request_geocode(', '.join([city, state_abbr, 'USA']))

    if coords is None:
        return None, None, False

    lat, lng = coords
    _store_cache(city, state_abbr, zip_code, lat, lng, street)
    return lat, lng, True
