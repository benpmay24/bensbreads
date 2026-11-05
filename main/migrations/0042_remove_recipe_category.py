# All recipes are bread recipes now, so the bread/other category is no longer needed.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0041_clear_recipes'),
    ]

    operations = [
        migrations.RemoveField(model_name='recipe', name='category'),
    ]
