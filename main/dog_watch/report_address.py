"""Extract facility street addresses from USDA inspection report PDFs."""
import logging
import re
from io import BytesIO

import requests

logger = logging.getLogger(__name__)

HEADERS = {'User-Agent': "Ben's Breads Dog Watch (bensbreads.com)"}

# Appears on page 1 of every AWA inspection report, before "Customer ID:"
_ADDRESS_BLOCK = re.compile(
    r'Page\s+\d+\s+of\s+\d+\s*\n'
    r'(?P<name>.+?)\n'
    r'(?P<street>.+?)\n'
    r'(?P<citystatezip>[A-Za-z0-9 .\'\-/]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)\s*\n'
    r'Customer ID:',
    re.DOTALL,
)

_CITY_STATE_ZIP = re.compile(
    r'^(.+?),\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?$',
)


def parse_address_from_report_text(text: str) -> dict[str, str]:
    """Parse the facility address block from inspection report PDF text."""
    if not text:
        return {}

    match = _ADDRESS_BLOCK.search(text)
    if not match:
        return {}

    csz = _CITY_STATE_ZIP.match(match.group('citystatezip').strip())
    if not csz:
        return {}

    street = match.group('street').strip()
    if not street or street.lower().startswith('united states'):
        return {}

    return {
        'street_address': street,
        'city': csz.group(1).strip().title(),
        'state': csz.group(2),
        'zip_code': csz.group(3),
    }


def fetch_address_from_report_url(url: str) -> dict[str, str]:
    """Download an inspection report PDF and extract the facility address."""
    if not url:
        return {}

    try:
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('Failed to download inspection report %s: %s', url[:80], exc)
        return {}

    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning('pypdf not installed; cannot extract addresses from reports')
        return {}

    try:
        reader = PdfReader(BytesIO(response.content))
        if not reader.pages:
            return {}
        text = reader.pages[0].extract_text() or ''
    except Exception as exc:
        logger.warning('Failed to read inspection report PDF: %s', exc)
        return {}

    return parse_address_from_report_text(text)
