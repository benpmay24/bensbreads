# Clears every existing recipe (with its ingredients, instructions and image) and
# removes the bread/other category: from now on all recipes are bread recipes.
#
# The deletion is irreversible; rolling this migration back restores the column
# but not the recipes.

from django.db import migrations


def delete_all_recipes(apps, schema_editor):
    Recipe = apps.get_model('main', 'Recipe')
    for recipe in Recipe.objects.exclude(image='').exclude(image__isnull=True):
        try:
            recipe.image.delete(save=False)
        except Exception:
            pass  # A missing or unreachable image file shouldn't block clearing the rows
    # Ingredients and instructions are removed by the CASCADE foreign keys.
    Recipe.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0040_remove_unused_features'),
    ]

    operations = [
        migrations.RunPython(delete_all_recipes, migrations.RunPython.noop),
        migrations.RemoveField(model_name='recipe', name='category'),
    ]
