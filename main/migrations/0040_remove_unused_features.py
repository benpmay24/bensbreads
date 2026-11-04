# Removes Dog Watch, Clash Center, Daily Update and Reviews.
#
# The database side drops each table only if it exists, so this works even on a
# database where some of these tables were never created or were already removed.
# (Removing foreign keys one at a time also fails on SQLite because of unique
# constraints, so the tables are dropped directly, dependents first.)

from django.db import migrations

TABLES = [
    # Dog Watch
    'main_facilityviolation',
    'main_facilityinspectionreport',
    'main_puppymillfacility',
    'main_dogwatchsyncstate',
    # Clash Center
    'main_clashbattle',
    'main_clashcard',
    'main_clashplayer',
    'main_clashcentersyncstate',
    # Daily Update
    'main_dailyupdate',
    # Reviews
    'main_review',
]


def drop_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())
    cascade = ' CASCADE' if connection.vendor == 'postgresql' else ''
    for table in TABLES:
        if table in existing:
            schema_editor.execute(f'DROP TABLE {schema_editor.quote_name(table)}{cascade}')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0039_starhold_result'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(drop_tables, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.DeleteModel(name='FacilityViolation'),
                migrations.DeleteModel(name='FacilityInspectionReport'),
                migrations.DeleteModel(name='PuppyMillFacility'),
                migrations.DeleteModel(name='DogWatchSyncState'),
                migrations.DeleteModel(name='ClashBattle'),
                migrations.DeleteModel(name='ClashCard'),
                migrations.DeleteModel(name='ClashPlayer'),
                migrations.DeleteModel(name='ClashCenterSyncState'),
                migrations.DeleteModel(name='DailyUpdate'),
                migrations.DeleteModel(name='Review'),
            ],
        ),
    ]
