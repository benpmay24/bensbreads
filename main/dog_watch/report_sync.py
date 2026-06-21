"""Sync inspection reports and individual violations into the database."""
import logging
from datetime import date, datetime

from django.conf import settings
from django.db.models import Count

from main.models import FacilityInspectionReport, FacilityViolation, PuppyMillFacility
from main.dog_watch.aphis_client import _int_field
from main.dog_watch.report_pdf import fetch_report_pdf_text
from main.dog_watch.report_violations import parse_violations_from_report_text, pdf_reports_no_violations

logger = logging.getLogger(__name__)

MAX_PARSE_ATTEMPTS = 3
PDF_MAX_PAGES = 5


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


def known_report_urls(facility: PuppyMillFacility) -> set[str]:
    """Report URLs already stored for this facility."""
    return set(
        FacilityInspectionReport.objects.filter(facility=facility).values_list('report_url', flat=True)
    )


def find_new_inspections(
    facility: PuppyMillFacility,
    inspections: list[dict],
) -> list[dict]:
    """Return APHIS inspection records whose PDFs are not yet in the database."""
    known = known_report_urls(facility)
    return [
        insp for insp in inspections
        if insp.get('reportLink') and insp['reportLink'] not in known
    ]


def create_new_inspection_reports(
    facility: PuppyMillFacility,
    inspections: list[dict],
) -> list[FacilityInspectionReport]:
    """
    Insert report records for inspections not yet stored.
    Never modifies existing rows — already-processed reports are left alone.
    """
    created: list[FacilityInspectionReport] = []
    known = known_report_urls(facility)

    for insp in inspections:
        url = insp.get('reportLink') or ''
        if not url or url in known:
            continue

        report = FacilityInspectionReport.objects.create(
            facility=facility,
            report_url=url,
            inspection_date=parse_inspection_date(
                insp.get('inspectionDate') or insp.get('inspectionDateString')
            ),
            inspection_type=(insp.get('inspectionType') or insp.get('type') or '')[:80],
            direct_count=_int_field(insp, 'direct', 'directViolations'),
            critical_count=_int_field(insp, 'critical', 'criticalViolations'),
            non_critical_count=_int_field(insp, 'nonCritical', 'nonCriticalViolations'),
            teachable_count=_int_field(insp, 'teachableMoments', 'teachable'),
            violations_parsed=False,
        )
        created.append(report)
        known.add(url)

    return created


def pending_violation_reports_queryset():
    """Reports that still need a first-time PDF violation parse."""
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


def _create_fallback_violations(report: FacilityInspectionReport) -> int:
    """
    When PDF text cannot be parsed after several attempts, store summary rows
    so the report clears the queue and links to the PDF for full details.
    """
    specs = (
        (FacilityViolation.Category.DIRECT, report.direct_count),
        (FacilityViolation.Category.CRITICAL, report.critical_count),
        (FacilityViolation.Category.NON_CRITICAL, report.non_critical_count),
        (FacilityViolation.Category.TEACHABLE, report.teachable_count),
    )
    created = 0
    for category, count in specs:
        for _ in range(count):
            FacilityViolation.objects.create(
                facility=report.facility,
                report=report,
                category=category,
                section='',
                title='See inspection report',
                description='Full violation details are in the linked inspection report PDF.',
                inspection_date=report.inspection_date,
            )
            created += 1
    return created


def parse_report_violations(report: FacilityInspectionReport) -> int | None:
    """
    Download a report PDF and store individual violations (first time only).
    Returns the number saved, 0 if confirmed none, or None if parsing should retry.
    """
    if report.violations_parsed:
        return report.violations.count()

    if report.total_violations == 0 and report.teachable_count == 0:
        report.violations_parsed = True
        report.save(update_fields=['violations_parsed', 'updated_at'])
        return 0

    if report.parse_attempts >= MAX_PARSE_ATTEMPTS:
        report.violations.all().delete()
        created = _create_fallback_violations(report)
        report.violations_parsed = True
        report.save(update_fields=['violations_parsed', 'updated_at'])
        logger.info(
            'Using PDF fallback for %s report %s after %s attempts (%s rows)',
            report.facility.license_number, report.id, report.parse_attempts, created,
        )
        return created

    text = fetch_report_pdf_text(report.report_url, max_pages=PDF_MAX_PAGES)
    if not text:
        report.parse_attempts += 1
        report.save(update_fields=['parse_attempts', 'updated_at'])
        logger.warning(
            'Could not read PDF for %s report %s (attempt %s/%s)',
            report.facility.license_number, report.id, report.parse_attempts, MAX_PARSE_ATTEMPTS,
        )
        return None

    if pdf_reports_no_violations(text):
        report.violations_parsed = True
        report.save(update_fields=['violations_parsed', 'updated_at'])
        return 0

    parsed = parse_violations_from_report_text(text)
    if parsed:
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

    expected = report.total_violations + report.teachable_count
    if expected > 0:
        report.parse_attempts += 1
        report.save(update_fields=['parse_attempts', 'updated_at'])
        if report.parse_attempts >= MAX_PARSE_ATTEMPTS:
            report.violations.all().delete()
            created = _create_fallback_violations(report)
            report.violations_parsed = True
            report.save(update_fields=['violations_parsed', 'updated_at'])
            logger.info(
                'Using PDF fallback for %s report %s after %s attempts (%s rows)',
                report.facility.license_number, report.id, report.parse_attempts, created,
            )
            return created
        logger.warning(
            'Parsed 0 violations from PDF but API reports %s for %s report %s '
            '(attempt %s/%s)',
            expected,
            report.facility.license_number,
            report.id,
            report.parse_attempts,
            MAX_PARSE_ATTEMPTS,
        )
        return None

    report.violations_parsed = True
    report.save(update_fields=['violations_parsed', 'updated_at'])
    return 0


def parse_violations_for_reports(reports: list[FacilityInspectionReport]) -> int:
    """Parse violations for newly added reports only. Skips already-parsed rows."""
    total = 0
    for report in reports:
        if report.violations_parsed:
            continue
        try:
            count = parse_report_violations(report)
            if count is not None:
                total += count
        except Exception:
            logger.exception(
                'Failed to parse violations for %s report %s',
                report.facility.license_number,
                report.id,
            )
    return total


def parse_pending_violations_batch(
    batch_size: int | None = None,
    *,
    created_since=None,
) -> dict:
    """
    First-time parse of report PDFs that have never been processed.
    Already-parsed reports (violations_parsed=True) are never touched.
    """
    if batch_size is None:
        batch_size = getattr(settings, 'DOG_WATCH_VIOLATIONS_BATCH_SIZE', 40)

    qs = pending_violation_reports_queryset().order_by('-inspection_date', 'id')
    if created_since is not None:
        qs = qs.filter(created_at__gte=created_since)

    pending = list(qs[:batch_size])

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
