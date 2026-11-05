# Clears every existing recipe (with its ingredients, instructions and image).
# From now on all recipes are bread recipes; the category column is dropped in 0042.
#
# This is kept separate from the schema change on purpose: on PostgreSQL, deleting
# rows with cascading foreign keys leaves deferred trigger events, and ALTER TABLE
# on the same table in the same transaction then fails with "pending trigger events".
#
# The deletion is irreversible; rolling this migration back does not restore recipes.

from django.db import migrations, transaction


def delete_all_recipes(apps, schema_editor):
    Recipe = apps.get_model('main', 'Recipe')
    images = [r.image for r in Recipe.objects.exclude(image='').exclude(image__isnull=True)]

    # Ingredients and instructions are removed by the CASCADE foreign keys.
    Recipe.objects.all().delete()

    # Files can't be rolled back, so only remove them once the row deletion has committed.
    def delete_files():
        for image in images:
            try:
                image.storage.delete(image.name)
            except Exception:
                pass  # A missing or unreachable file shouldn't matter at this point
    transaction.on_commit(delete_files, using=schema_editor.connection.alias)


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0040_remove_unused_features'),
    ]

    operations = [
        migrations.RunPython(delete_all_recipes, migrations.RunPython.noop),
    ]
