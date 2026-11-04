# Removes Dog Watch, Clash Center, Daily Update and Reviews.
# Tables are dropped directly (dependents first) rather than removing foreign
# keys one at a time, which fails on SQLite because of unique constraints.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0039_starhold_result'),
    ]

    operations = [
        # Dog Watch
        migrations.DeleteModel(name='FacilityViolation'),
        migrations.DeleteModel(name='FacilityInspectionReport'),
        migrations.DeleteModel(name='PuppyMillFacility'),
        migrations.DeleteModel(name='DogWatchSyncState'),
        # Clash Center
        migrations.DeleteModel(name='ClashBattle'),
        migrations.DeleteModel(name='ClashCard'),
        migrations.DeleteModel(name='ClashPlayer'),
        migrations.DeleteModel(name='ClashCenterSyncState'),
        # Daily Update
        migrations.DeleteModel(name='DailyUpdate'),
        # Reviews
        migrations.DeleteModel(name='Review'),
    ]
