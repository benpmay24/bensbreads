from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0030_puppymillfacility'),
    ]

    operations = [
        migrations.CreateModel(
            name='DogWatchSyncState',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('is_running', models.BooleanField(default=False)),
                ('last_sync_at', models.DateTimeField(blank=True, null=True)),
                ('last_usda_import_at', models.DateTimeField(blank=True, null=True)),
                ('last_summary', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'verbose_name': 'Dog Watch sync state',
            },
        ),
    ]
