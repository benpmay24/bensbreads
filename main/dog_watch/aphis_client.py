"""Client for the USDA APHIS Public Search Tool (inspection reports API)."""
import json
import re
import time
import logging
from typing import Any, Generator

import requests
import urllib3

urllib3.disable_warnings()

logger = logging.getLogger(__name__)

AURA_URL = 'https://efile.aphis.usda.gov/PublicSearchTool/s/sfsites/aura'
FWUID_URL = 'https://aphis.my.site.com/PublicSearchTool/s/inspection-reports'

HEADERS = {
    'User-Agent': "Ben's Breads Dog Watch (bensbreads.com)",
    'Accept': '*/*',
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'Origin': 'https://efile.aphis.usda.gov',
}

AURA_CONTEXT: dict[str, Any] = {
    'mode': 'PROD',
    'app': 'siteforce:communityApp',
    'loaded': {
        'APPLICATION@markup://siteforce:communityApp': '11hSeJMz5y2BtbPLHOZFww',
    },
    'dn': [],
    'globals': {},
    'uad': False,
}

_fwuid_cache: str | None = None


def _int_field(record: dict[str, Any], *keys: str) -> int:
    for key in keys:
        val = record.get(key)
        if val is not None and val != '':
            return int(val)
    return 0


def get_fwuid() -> str:
    global _fwuid_cache
    if _fwuid_cache:
        return _fwuid_cache
    res = requests.get(FWUID_URL, timeout=60)
    match = re.search(r'%22fwuid%22%3A%22([^%]+)%22%2C', res.content.decode('utf-8'))
    if not match:
        raise ValueError('Cannot find APHIS fwuid token.')
    _fwuid_cache = match.group(1)
    AURA_CONTEXT['fwuid'] = _fwuid_cache
    return _fwuid_cache


def _make_payload(index: int, criteria: dict[str, Any]) -> dict[str, str]:
    action = {
        'descriptor': 'apex://EFL_PSTController/ACTION$doIRSearch_UI',
        'params': {
            'searchCriteria': {'index': index, 'numberOfRows': 100, **criteria},
            'getCount': True,
        },
    }
    return {
        'message': '{"actions":[' + json.dumps(action) + ']}',
        'aura.context': json.dumps({**AURA_CONTEXT, 'fwuid': get_fwuid()}),
        'aura.token': 'null',
    }


def _fetch_page(index: int, criteria: dict[str, Any]) -> dict[str, Any] | None:
    for attempt in range(2):
        try:
            res = requests.post(
                AURA_URL,
                headers=HEADERS,
                data=_make_payload(index, criteria),
                verify=False,
                timeout=30,
            )
            decoded = res.content.decode('utf-8')
            if 'Framework has been updated' in decoded:
                global _fwuid_cache
                _fwuid_cache = None
                get_fwuid()
                continue
            data = res.json()['actions'][0]['returnValue']
            if data is None:
                time.sleep(2 * (attempt + 1))
                continue
            return data
        except (requests.RequestException, KeyError, json.JSONDecodeError) as exc:
            logger.warning('APHIS fetch attempt %s failed: %s', attempt + 1, exc)
            time.sleep(2 * (attempt + 1))
    return None


def search_inspections(
    criteria: dict[str, Any],
    max_pages: int = 1,
) -> Generator[dict[str, Any], None, None]:
    """Yield inspection records matching the given search criteria."""
    data = _fetch_page(0, criteria)
    if not data:
        return
    yield from data.get('results', [])
    if max_pages <= 1:
        return
    total = data.get('totalCount', 0)
    pages = min(max_pages, 21, (total // 100) + 1)
    for page in range(1, pages):
        time.sleep(0.3)
        page_data = _fetch_page(page, criteria)
        if not page_data or not page_data.get('results'):
            break
        yield from page_data['results']


def _inspection_report(insp: dict[str, Any]) -> dict[str, Any]:
    return {
        'date': insp.get('inspectionDate', '') or insp.get('inspectionDateString', ''),
        'url': insp.get('reportLink', ''),
        'direct': _int_field(insp, 'direct', 'directViolations'),
        'critical': _int_field(insp, 'critical', 'criticalViolations'),
        'non_critical': _int_field(insp, 'nonCritical', 'nonCriticalViolations'),
        'teachable': _int_field(insp, 'teachableMoments', 'teachable'),
    }


def _build_inspection_reports(inspections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Include every report with violations plus the 5 most recent clean reports."""
    reports = [_inspection_report(insp) for insp in inspections]

    def has_violation(r: dict[str, Any]) -> bool:
        return (r['direct'] + r['critical'] + r['non_critical'] + r['teachable']) > 0

    violating = sorted(
        [r for r in reports if has_violation(r)],
        key=lambda r: r['date'],
        reverse=True,
    )
    clean = sorted(
        [r for r in reports if not has_violation(r)],
        key=lambda r: r['date'],
        reverse=True,
    )
    return (violating + clean[:5])[:50]


def enrich_facility(license_number: str) -> dict[str, Any]:
    """Fetch inspection history and facility details for a license number."""
    inspections = list(search_inspections({'certNumber': license_number}))
    if not inspections:
        return {}

    latest = inspections[0]
    direct = sum(_int_field(i, 'direct', 'directViolations') for i in inspections)
    critical = sum(_int_field(i, 'critical', 'criticalViolations') for i in inspections)
    non_critical = sum(_int_field(i, 'nonCritical', 'nonCriticalViolations') for i in inspections)

    species = set()
    for insp in inspections:
        for field in ('species', 'speciesInspected', 'animalType'):
            val = insp.get(field)
            if val:
                for part in re.split(r'[,;/]', str(val)):
                    part = part.strip()
                    if part:
                        species.add(part)

    reports = _build_inspection_reports(inspections)

    latest_report_url = ''
    dated = [
        insp for insp in inspections
        if insp.get('reportLink') and (insp.get('inspectionDate') or insp.get('inspectionDateString'))
    ]
    if dated:
        latest_insp = max(
            dated,
            key=lambda i: i.get('inspectionDate') or i.get('inspectionDateString') or '',
        )
        latest_report_url = latest_insp.get('reportLink') or ''

    owners = []
    for field in ('legalName', 'customerName', 'ownerName'):
        val = latest.get(field)
        if val and val not in owners:
            owners.append(val)

    dog_keywords = ('dog', 'canine', 'puppy', 'puppies')
    species_text = ' '.join(species).lower()
    is_dog = any(kw in species_text for kw in dog_keywords) if species else True

    return {
        'street_address': latest.get('streetAddress') or latest.get('address') or '',
        'city': latest.get('city') or '',
        'state': latest.get('state') or '',
        'zip_code': latest.get('zip') or latest.get('zipCode') or '',
        'owners': owners,
        'dog_breeds': sorted(species) if species else [],
        'is_dog_facility': is_dog,
        'violation_count': direct + critical + non_critical,
        'direct_violations': direct,
        'critical_violations': critical,
        'inspection_reports': reports,
        'latest_report_url': latest_report_url,
        'total_inspections': len(inspections),
        'usda_profile_url': (
            f'https://efile.aphis.usda.gov/PublicSearchTool/s/'
            f'inspection-reports?certNumber={license_number}'
        ),
    }
