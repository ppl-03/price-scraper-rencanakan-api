# db_pricing/migrations/0006_merge_20251022.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('db_pricing', '0005_juraganmaterialproduct'),
        ('db_pricing', '0005_merge_20251022_2312'),
    ]

    operations = [
        # If the two migrations touch disjoint models/fields, this can be empty.
        # If they contain conflicting operations, resolve them here by
        # including the final operations needed to put the DB schema in the
        # intended state. Example: merging two AddField operations into a single state.
    ]