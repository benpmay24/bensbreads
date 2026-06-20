from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0031_dogwatchsyncstate'),
    ]

    operations = [
        migrations.AddField(
            model_name='puppymillfacility',
            name='coordinates_geocoded',
            field=models.BooleanField(default=False),
        ),
    ]
