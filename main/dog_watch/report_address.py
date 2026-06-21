"""Extract facility street addresses from USDA inspection report PDFs."""
import re

from main.dog_watch.report_pdf import fetch_report_pdf_text

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
    text = fetch_report_pdf_text(url, max_pages=1)
    return parse_address_from_report_text(text)
