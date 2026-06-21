"""Download and extract text from USDA inspection report PDFs."""
import logging
from io import BytesIO

import requests

logger = logging.getLogger(__name__)

HEADERS = {'User-Agent': "Ben's Breads Dog Watch (bensbreads.com)"}


def fetch_report_pdf_text(url: str, max_pages: int | None = None) -> str:
    """Download an inspection report PDF and return extracted text."""
    if not url:
        return ''

    try:
        response = requests.get(url, headers=HEADERS, timeout=(10, 30))
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning('Failed to download inspection report %s: %s', url[:80], exc)
        return ''

    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning('pypdf not installed; cannot read inspection report PDFs')
        return ''

    try:
        reader = PdfReader(BytesIO(response.content))
        pages = reader.pages[:max_pages] if max_pages else reader.pages
        return '\n'.join((page.extract_text() or '') for page in pages)
    except Exception as exc:
        logger.warning('Failed to read inspection report PDF: %s', exc)
        return ''
