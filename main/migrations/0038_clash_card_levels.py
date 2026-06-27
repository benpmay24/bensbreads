from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0037_clash_center'),
    ]

    operations = [
        migrations.AddField(
            model_name='clashcard',
            name='max_level',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='clashcard',
            name='max_evolution_level',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
