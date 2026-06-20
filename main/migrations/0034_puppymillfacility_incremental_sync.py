from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0033_dogwatchsyncstate_progress'),
    ]

    operations = [
        migrations.AddField(
            model_name='puppymillfacility',
            name='processed_report_urls',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='puppymillfacility',
            name='last_checked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
