from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0032_puppymillfacility_coordinates_geocoded'),
    ]

    operations = [
        migrations.AddField(
            model_name='dogwatchsyncstate',
            name='progress',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
