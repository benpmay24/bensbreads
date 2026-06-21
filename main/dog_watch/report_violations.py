"""Parse individual violations from USDA inspection report PDF text."""
import re

from main.dog_watch.report_pdf import fetch_report_pdf_text

SECTION_RE = re.compile(
    r'(?P<section>\d+\.\d+(?:\([a-z0-9]+\))+)\s*'
    r'(?P<flags>(?:Direct\s+Repeat|Critical\s+Repeat|Direct|Critical|Repeat|Teachable(?:\s+Moment)?)?)',
    re.IGNORECASE,
)

_END_RE = re.compile(
    r'\n(?:This inspection and exit|End of report|\*END OF REPORT\*|Additional Inspectors:)',
    re.IGNORECASE,
)


def _category_from_flags(flags: str) -> str:
    normalized = (flags or '').lower()
    if 'direct' in normalized:
        return 'direct'
    if 'critical' in normalized:
        return 'critical'
    if 'teachable' in normalized:
        return 'teachable'
    return 'non_critical'


def _split_title_and_description(body: str) -> tuple[str, str]:
    body = body.strip()
    if not body:
        return '', ''

    title_match = re.match(r'^(.+?\.)\s*(.*)$', body, re.DOTALL)
    if not title_match:
        return '', body.strip()

    title = title_match.group(1).strip()
    description = title_match.group(2).strip()
    if description:
        return title, description

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(lines) <= 1:
        return title, ''
    return lines[0], ' '.join(lines[1:])


def parse_violations_from_report_text(text: str) -> list[dict]:
    """Extract individual violations from inspection report PDF text."""
    if not text:
        return []

    end_match = _END_RE.search(text)
    narrative = text[:end_match.start()] if end_match else text

    type_match = re.search(r'Type:\s*.+?\nDate:\s*.+?\n', narrative, re.IGNORECASE | re.DOTALL)
    if type_match:
        narrative = narrative[type_match.end():]

    violations = []
    matches = list(SECTION_RE.finditer(narrative))
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(narrative)
        body = narrative[match.end():next_start].strip()
        title, description = _split_title_and_description(body)
        flags = (match.group('flags') or '').strip()
        violations.append({
            'section': match.group('section'),
            'category': _category_from_flags(flags),
            'is_repeat': 'repeat' in flags.lower(),
            'title': title,
            'description': description,
        })
    return violations


def fetch_violations_from_report_url(url: str) -> list[dict]:
    """Download a report PDF and return parsed violations."""
    text = fetch_report_pdf_text(url, max_pages=3)
    return parse_violations_from_report_text(text)
