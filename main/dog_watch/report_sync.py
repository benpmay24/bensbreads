"""Sync inspection reports and individual violations into the database."""
import logging
from datetime import date, datetime

from django.db.models import Count

from main.models import FacilityInspectionReport, FacilityViolation, PuppyMillFacility
from main.dog_watch.aphis_client import _int_field
from main.dog_watch.report_violations import fetch_violations_from_report_url

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


def parse_report_violations(report: FacilityInspectionReport) -> int:
    """Download a report PDF and store individual violations. Returns count saved."""
    if report.violations_parsed:
        return report.violations.count()

    if report.total_violations == 0 and report.teachable_count == 0:
        report.violations_parsed = True
        report.save(update_fields=['violations_parsed', 'updated_at'])
        return 0

    parsed = fetch_violations_from_report_url(report.report_url)
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


def parse_unparsed_report_violations(reports: list[FacilityInspectionReport]) -> int:
    """Parse violations for reports that have not been processed yet."""
    parsed_total = 0
    for report in reports:
        if report.violations_parsed:
            continue
        if report.total_violations == 0 and report.teachable_count == 0:
            report.violations_parsed = True
            report.save(update_fields=['violations_parsed', 'updated_at'])
            continue
        try:
            parsed_total += parse_report_violations(report)
        except Exception:
            logger.exception(
                'Failed to parse violations for %s report %s',
                report.facility.license_number,
                report.report_url[:80],
            )
    return parsed_total


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
