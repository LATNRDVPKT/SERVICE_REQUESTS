# Renames the stored Responsibility value "IALERT" to "AL" on existing rows,
# matching the updated RESPONSIBILITY_MAP in constants.py (IALERT is no
# longer a responsibility bucket — AL replaces it everywhere).
from django.db import migrations


def ialert_to_al(apps, schema_editor):
    DirectCall = apps.get_model("crsc_calls", "DirectCall")
    DirectCallUpdate = apps.get_model("crsc_calls", "DirectCallUpdate")
    DirectCall.objects.filter(responsibility="IALERT").update(responsibility="AL")
    DirectCallUpdate.objects.filter(responsibility="IALERT").update(responsibility="AL")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crsc_calls", "0005_backfill_directcall_responsibility"),
    ]

    operations = [
        migrations.RunPython(ialert_to_al, noop_reverse),
    ]
