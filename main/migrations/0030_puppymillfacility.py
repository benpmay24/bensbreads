from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0029_remove_vaccinerecord_document'),
    ]

    operations = [
        migrations.CreateModel(
            name='PuppyMillFacility',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('license_number', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=300)),
                ('dba_name', models.CharField(blank=True, max_length=300)),
                ('license_type', models.CharField(blank=True, max_length=100)),
                ('street_address', models.CharField(blank=True, max_length=300)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('state', models.CharField(blank=True, max_length=2)),
                ('zip_code', models.CharField(blank=True, max_length=10)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('owners', models.JSONField(blank=True, default=list)),
                ('suppliers', models.JSONField(blank=True, default=list)),
                ('dog_breeds', models.JSONField(blank=True, default=list)),
                ('news_articles', models.JSONField(blank=True, default=list)),
                ('violation_count', models.PositiveIntegerField(default=0)),
                ('direct_violations', models.PositiveIntegerField(default=0)),
                ('critical_violations', models.PositiveIntegerField(default=0)),
                ('inspection_reports', models.JSONField(blank=True, default=list)),
                ('usda_profile_url', models.URLField(blank=True)),
                ('source_notes', models.TextField(blank=True)),
                ('is_dog_facility', models.BooleanField(default=True)),
                ('license_expiration', models.DateField(blank=True, null=True)),
                ('last_scraped_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'puppy mill facilities',
                'ordering': ['state', 'city', 'name'],
            },
        ),
    ]
