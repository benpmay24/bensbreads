"""Scrape USDA licensee data and enrich with APHIS inspection records."""
import io
import logging
import time
from datetime import datetime

import openpyxl
import requests
from django.utils import timezone

from main.models import PuppyMillFacility
from main.dog_watch.aphis_client import enrich_facility
from main.dog_watch.geocoder import geocode, normalize_state
from main.dog_watch.report_address import fetch_address_from_report_url
from main.dog_watch.news import fetch_news
from main.dog_watch import sync_state

logger = logging.getLogger(__name__)

USDA_LICENSEE_URL = (
    'https://www.aphis.usda.gov/sites/default/files/'
    'list-of-active-licensees-and-registrants.xlsx'
)
TARGET_LICENSE_TYPES = {'Class A - Breeder', 'Class B - Dealer'}
HEADER_ROW_LABEL = 'Registration Type'


def set_progress(phase: str, current: int, total: int, message: str = '') -> None:
    state = sync_state.get_sync_state()
    state.progress = {
        'running': True,
        'phase': phase,
        'current': current,
        'total': total,
        'message': message,
        'updated_at': timezone.now().isoformat(),
    }
    state.save(update_fields=['progress'])


def clear_progress() -> None:
    state = sync_state.get_sync_state()
    state.progress = {'running': False}
    state.save(update_fields=['progress'])


def get_progress() -> dict:
    return sync_state.get_progress()


def _parse_expiration(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), '%m/%d/%Y').date()
    except ValueError:
        return None


def fetch_usda_licensees() -> list[dict]:
    """Download and parse the USDA active licensees spreadsheet."""
    set_progress('download', 0, 1, 'Downloading USDA licensee data...')
    res = requests.get(USDA_LICENSEE_URL, timeout=60)
    res.raise_for_status()
    wb = openpyxl.load_workbook(io.BytesIO(res.content), read_only=True)
    ws = wb[wb.sheetnames[0]]

    facilities = []
    headers = None
    for row in ws.iter_rows(values_only=True):
        if row[1] == HEADER_ROW_LABEL:
            headers = row
            continue
        if not headers or not row[1] or not str(row[1]).startswith('Class '):
            continue
        license_type = row[1]
        if license_type not in TARGET_LICENSE_TYPES:
            continue
        row_data = dict(zip(headers, row))
        license_number = row_data.get('APHIS Registration Number') or row_data.get('APHIS License Number') or ''
        if not license_number:
            continue
        facilities.append({
            'license_number': str(license_number).strip(),
            'license_type': license_type,
            'name': (row_data.get('Account Name') or '').strip(),
            'dba_name': (row_data.get('DBA Name(s)') or '').strip(),
            'city': (row_data.get('Mailing City') or row_data.get('City') or '').strip(),
            'state': (row_data.get('State Abbreviation') or row_data.get('State') or '').strip(),
            'license_expiration': _parse_expiration(row_data.get('Expiration Date')),
            'usda_profile_url': (
                f'https://efile.aphis.usda.gov/PublicSearchTool/s/'
                f'inspection-reports?certNumber={license_number}'
            ),
        })
    return facilities


def _geocode_facility(facility: PuppyMillFacility) -> bool:
    """Update facility coordinates from its address fields. Returns True if geocoded."""
    state = normalize_state(facility.state)
    if not facility.city or not state:
        return False

    lat, lng, geocoded = geocode(
        facility.name,
        facility.city,
        state,
        facility.street_address,
        facility.zip_code,
    )
    if not geocoded or lat is None or lng is None:
        return False

    facility.latitude = lat
    facility.longitude = lng
    facility.coordinates_geocoded = True
    if state != facility.state:
        facility.state = state
    return True


def _upsert_base_record(data: dict) -> tuple[PuppyMillFacility, bool]:
    owners = [data['name']] if data.get('name') else []
    defaults = {
        'name': data['name'],
        'dba_name': data.get('dba_name', ''),
        'license_type': data['license_type'],
        'city': data.get('city', ''),
        'state': normalize_state(data.get('state', '')),
        'license_expiration': data.get('license_expiration'),
        'usda_profile_url': data.get('usda_profile_url', ''),
        'owners': owners,
    }
    facility, created = PuppyMillFacility.objects.update_or_create(
        license_number=data['license_number'],
        defaults=defaults,
    )
    return facility, created


def import_usda_facilities() -> dict:
    """Import or update all facilities from the USDA spreadsheet."""
    summary = {'created': 0, 'updated': 0, 'errors': 0, 'total_usda': 0}

    try:
        usda_facilities = fetch_usda_licensees()
    except Exception as exc:
        logger.exception('Failed to fetch USDA licensee data')
        summary['error'] = str(exc)
        return summary

    summary['total_usda'] = len(usda_facilities)
    total = len(usda_facilities)

    for i, data in enumerate(usda_facilities, start=1):
        if i % 50 == 0 or i == total:
            set_progress('import', i, total, f'Importing USDA records ({i}/{total})...')
        try:
            _, created = _upsert_base_record(data)
            if created:
                summary['created'] += 1
            else:
                summary['updated'] += 1
        except Exception:
            logger.exception('Error importing %s', data.get('license_number'))
            summary['errors'] += 1

    return summary


def _enrich_record(
    facility: PuppyMillFacility,
    fetch_news_articles: bool = False,
) -> None:
    try:
        aphis_data = enrich_facility(facility.license_number)
    except Exception as exc:
        logger.warning('APHIS enrichment failed for %s: %s', facility.license_number, exc)
        aphis_data = {}

    if aphis_data:
        if aphis_data.get('street_address'):
            facility.street_address = aphis_data['street_address']
        if aphis_data.get('city'):
            facility.city = aphis_data['city']
        if aphis_data.get('state'):
            facility.state = normalize_state(aphis_data['state'])
        if aphis_data.get('zip_code'):
            facility.zip_code = aphis_data['zip_code']
        if aphis_data.get('owners'):
            facility.owners = aphis_data['owners']
        if aphis_data.get('dog_breeds'):
            facility.dog_breeds = aphis_data['dog_breeds']
        facility.is_dog_facility = aphis_data.get('is_dog_facility', True)
        facility.violation_count = aphis_data.get('violation_count', 0)
        facility.direct_violations = aphis_data.get('direct_violations', 0)
        facility.critical_violations = aphis_data.get('critical_violations', 0)
        facility.inspection_reports = aphis_data.get('inspection_reports', [])
        if aphis_data.get('usda_profile_url'):
            facility.usda_profile_url = aphis_data['usda_profile_url']

        report_url = aphis_data.get('latest_report_url') or ''
        if not report_url and facility.inspection_reports:
            report_url = facility.inspection_reports[0].get('url') or ''
        if report_url:
            pdf_address = fetch_address_from_report_url(report_url)
            if pdf_address.get('street_address'):
                facility.street_address = pdf_address['street_address']
            if pdf_address.get('city'):
                facility.city = pdf_address['city']
            if pdf_address.get('state'):
                facility.state = normalize_state(pdf_address['state'])
            if pdf_address.get('zip_code'):
                facility.zip_code = pdf_address['zip_code']

    _geocode_facility(facility)

    if fetch_news_articles and facility.violation_count > 0 and not facility.news_articles:
        facility.news_articles = fetch_news(facility.name, facility.city, facility.state)

    facility.last_scraped_at = timezone.now()
    facility.save()


def enrich_all_facilities(fetch_news_articles: bool = False) -> dict:
    """Enrich every dog facility from APHIS and update map coordinates."""
    summary = {'enriched': 0, 'errors': 0}
    facilities = list(
        PuppyMillFacility.objects.filter(is_dog_facility=True).order_by('id')
    )
    total = len(facilities)

    for i, facility in enumerate(facilities, start=1):
        set_progress(
            'enrich',
            i,
            total,
            f'Updating {facility.name} ({i}/{total})...',
        )
        try:
            _enrich_record(facility, fetch_news_articles=fetch_news_articles)
            summary['enriched'] += 1
            time.sleep(sync_state.aphis_delay())
        except Exception:
            logger.exception('Error enriching %s', facility.license_number)
            summary['errors'] += 1

    return summary


def geocode_all_facilities() -> dict:
    """Geocode every facility that still lacks verified map coordinates."""
    summary = {'geocoded': 0, 'skipped': 0, 'errors': 0}
    facilities = list(
        PuppyMillFacility.objects.filter(
            is_dog_facility=True,
            coordinates_geocoded=False,
        )
        .exclude(city='')
        .exclude(state='')
        .order_by('id')
    )
    total = len(facilities)

    for i, facility in enumerate(facilities, start=1):
        set_progress('geocode', i, total, f'Locating addresses ({i}/{total})...')
        try:
            if _geocode_facility(facility):
                facility.save(update_fields=['latitude', 'longitude', 'coordinates_geocoded', 'state'])
                summary['geocoded'] += 1
            else:
                summary['skipped'] += 1
        except Exception:
            logger.exception('Error geocoding %s', facility.license_number)
            summary['errors'] += 1

    return summary


def run_full_sync(
    force: bool = False,
    fetch_news_articles: bool = False,
) -> dict:
    """
    Full sync: import USDA list, enrich every facility, geocode any stragglers.
    Runs when due (every 24 hours) or when forced via Sync Now.
    """
    sync_state.clear_stale_lock()

    if get_progress().get('running'):
        return {'skipped': True, 'reason': 'sync already in progress'}

    if not force and not sync_state.is_sync_due():
        return {
            'skipped': True,
            'reason': 'sync not due yet',
            'next_sync_at': sync_state.next_sync_at().isoformat(),
        }

    lock = sync_state.try_acquire_lock()
    if lock is None:
        return {'skipped': True, 'reason': 'sync already running on another worker'}

    summary = {'skipped': False, 'status': 'complete'}

    try:
        set_progress('scheduled', 0, 0, 'Starting full Dog Watch update...')

        import_summary = import_usda_facilities()
        summary.update({
            'created': import_summary.get('created', 0),
            'updated': import_summary.get('updated', 0),
            'total_usda': import_summary.get('total_usda', 0),
        })
        if import_summary.get('error'):
            summary['error'] = import_summary['error']
            summary['status'] = 'error'
            sync_state.release_lock(lock, summary)
            return summary

        enrich_summary = enrich_all_facilities(fetch_news_articles=fetch_news_articles)
        summary['enriched'] = enrich_summary.get('enriched', 0)
        summary['errors'] = enrich_summary.get('errors', 0)

        geocode_summary = geocode_all_facilities()
        summary['geocoded'] = geocode_summary.get('geocoded', 0)
        summary['errors'] += geocode_summary.get('errors', 0)

        summary['mapped_count'] = PuppyMillFacility.objects.filter(
            is_dog_facility=True,
            coordinates_geocoded=True,
        ).count()
        summary['total_facilities'] = PuppyMillFacility.objects.filter(
            is_dog_facility=True,
        ).count()
        summary['completed_at'] = timezone.now().isoformat()
        summary['next_sync_at'] = sync_state.next_sync_at().isoformat()

        logger.info('Dog Watch full sync complete: %s', summary)
        sync_state.release_lock(lock, summary)
        return summary
    except Exception as exc:
        summary['status'] = 'error'
        summary['error'] = str(exc)
        sync_state.release_lock(lock, summary)
        raise
    finally:
        pass


run_scheduled_sync = run_full_sync


def scrape_puppy_mills(
    enrich: bool = True,
    fetch_news_articles: bool = False,
    force_import: bool = False,
) -> dict:
    """CLI entry point: import USDA data and optionally run a full sync."""
    summary = {'created': 0, 'updated': 0, 'enriched': 0, 'errors': 0, 'total_usda': 0}

    if force_import or PuppyMillFacility.objects.count() == 0:
        import_summary = import_usda_facilities()
        summary.update(import_summary)
        if import_summary.get('error'):
            return summary

    if enrich:
        enrich_summary = enrich_all_facilities(fetch_news_articles=fetch_news_articles)
        summary['enriched'] = enrich_summary.get('enriched', 0)
        summary['errors'] += enrich_summary.get('errors', 0)
        geocode_summary = geocode_all_facilities()
        summary['geocoded'] = geocode_summary.get('geocoded', 0)
        summary['errors'] += geocode_summary.get('errors', 0)

    return summary
