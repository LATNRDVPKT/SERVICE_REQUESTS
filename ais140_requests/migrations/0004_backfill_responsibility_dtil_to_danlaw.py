# Renames the stored Responsibility value "DTIL" to "DANLAW" on existing
# rows, matching the updated RESPONSIBILITY_MAP in constants.py (DTIL is no
# longer a responsibility bucket — DANLAW replaces it everywhere).
from django.db import migrations


def dtil_to_danlaw(apps, schema_editor):
    AIS140Request = apps.get_model("AIS140_FLOW", "AIS140Request")
    AIS140RequestUpdate = apps.get_model("AIS140_FLOW", "AIS140RequestUpdate")
    AIS140Request.objects.filter(responsibility="DTIL").update(responsibility="DANLAW")
    AIS140RequestUpdate.objects.filter(responsibility="DTIL").update(responsibility="DANLAW")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("AIS140_FLOW", "0003_alter_ais140request_customer_alternate_number_and_more"),
    ]

    operations = [
        migrations.RunPython(dtil_to_danlaw, noop_reverse),
    ]
