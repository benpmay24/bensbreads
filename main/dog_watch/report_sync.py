"""Sync inspection reports and individual violations into the database."""
import logging
from datetime import date, datetime

from django.conf import settings
from django.db.models import Count

from main.models import FacilityInspectionReport, FacilityViolation, PuppyMillFacility
from main.dog_watch.aphis_client import _int_field
from main.dog_watch.report_pdf import fetch_report_pdf_text
from main.dog_watch.report_violations import parse_violations_from_report_text

logger = logging.getLogger(__name__)


def parse_inspection_date(value: str | None) -> date | None:
    if not value:
        return None
    value = str(value).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d-%b-%Y', '%d-%B-%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def upsert_inspection_reports(
    facility: PuppyMillFacility,
    inspections: list[dict],
) -> list[FacilityInspectionReport]:
    """Create or update report records from APHIS inspection API data."""
    reports: list[FacilityInspectionReport] = []

    for insp in inspections:
        url = insp.get('reportLink') or ''
        if not url:
            continue

        inspection_date = parse_inspection_date(
            insp.get('inspectionDate') or insp.get('inspectionDateString')
        )
        defaults = {
            'inspection_date': inspection_date,
            'inspection_type': (insp.get('inspectionType') or insp.get('type') or '')[:80],
            'direct_count': _int_field(insp, 'direct', 'directViolations'),
            'critical_count': _int_field(insp, 'critical', 'criticalViolations'),
            'non_critical_count': _int_field(insp, 'nonCritical', 'nonCriticalViolations'),
            'teachable_count': _int_field(insp, 'teachableMoments', 'teachable'),
        }
        report, _created = FacilityInspectionReport.objects.update_or_create(
            facility=facility,
            report_url=url,
            defaults=defaults,
        )
        reports.append(report)

    return reports


def pending_violation_reports_queryset():
    """Reports that still need PDF violation parsing."""
    return (
        FacilityInspectionReport.objects.filter(violations_parsed=False)
        .exclude(
            direct_count=0,
            critical_count=0,
            non_critical_count=0,
            teachable_count=0,
        )
        .select_related('facility')
    )


def parse_report_violations(report: FacilityInspectionReport) -> int | None:
    """
    Download a report PDF and store individual violations.
    Returns the number saved, 0 if confirmed none, or None if parsing should retry.
    """
    if report.violations_parsed:
        return report.violations.count()

    if report.total_violations == 0 and report.teachable_count == 0:
        report.violations_parsed = True
        report.save(update_fields=['violations_parsed', 'updated_at'])
        return 0

    text = fetch_report_pdf_text(report.report_url, max_pages=3)
    if not text:
        logger.warning(
            'Could not read PDF for %s report %s — will retry later',
            report.facility.license_number,
            report.id,
        )
        return None

    parsed = parse_violations_from_report_text(text)
    expected = report.total_violations + report.teachable_count
    if not parsed and expected > 0:
        logger.warning(
            'Parsed 0 violations from PDF but API reports %s for %s report %s — will retry later',
            expected,
            report.facility.license_number,
            report.id,
        )
        return None

    report.violations.all().delete()
    for item in parsed:
        FacilityViolation.objects.create(
            facility=report.facility,
            report=report,
            category=item['category'],
            section=item['section'],
            title=item['title'][:300],
            description=item['description'],
            is_repeat=item['is_repeat'],
            inspection_date=report.inspection_date,
        )

    report.violations_parsed = True
    report.save(update_fields=['violations_parsed', 'updated_at'])
    return len(parsed)


def parse_pending_violations_batch(batch_size: int | None = None) -> dict:
    """
    Parse a batch of pending inspection report PDFs into FacilityViolation rows.
    Runs independently of the per-facility APHIS check so backlog clears even when
    facilities were recently checked.
    """
    if batch_size is None:
        batch_size = getattr(settings, 'DOG_WATCH_VIOLATIONS_BATCH_SIZE', 40)

    pending = list(
        pending_violation_reports_queryset().order_by('-inspection_date', 'id')[:batch_size]
    )

    parsed_reports = 0
    parsed_violations = 0
    retry_later = 0
    facility_ids: set[int] = set()

    for report in pending:
        try:
            count = parse_report_violations(report)
        except Exception:
            logger.exception(
                'Failed to parse violations for %s report %s',
                report.facility.license_number,
                report.id,
            )
            retry_later += 1
            continue

        if count is None:
            retry_later += 1
            continue

        parsed_reports += 1
        parsed_violations += count
        facility_ids.add(report.facility_id)

    for facility in PuppyMillFacility.objects.filter(id__in=facility_ids):
        recompute_facility_violation_counts(facility)

    remaining = pending_violation_reports_queryset().count()
    return {
        'violations_reports_parsed': parsed_reports,
        'violations_created': parsed_violations,
        'violations_parse_retries': retry_later,
        'violations_pending': remaining,
    }


def recompute_facility_violation_counts(facility: PuppyMillFacility) -> None:
    """Refresh denormalized violation totals on the facility."""
    counts = (
        FacilityViolation.objects.filter(facility=facility)
        .values('category')
        .annotate(total=Count('id'))
    )
    by_category = {row['category']: row['total'] for row in counts}

    if by_category:
        direct = by_category.get(FacilityViolation.Category.DIRECT, 0)
        critical = by_category.get(FacilityViolation.Category.CRITICAL, 0)
        non_critical = by_category.get(FacilityViolation.Category.NON_CRITICAL, 0)
        teachable = by_category.get(FacilityViolation.Category.TEACHABLE, 0)
    else:
        reports = FacilityInspectionReport.objects.filter(facility=facility)
        direct = sum(r.direct_count for r in reports)
        critical = sum(r.critical_count for r in reports)
        non_critical = sum(r.non_critical_count for r in reports)
        teachable = sum(r.teachable_count for r in reports)

    facility.direct_violations = direct
    facility.critical_violations = critical
    facility.violation_count = direct + critical + non_critical + teachable
