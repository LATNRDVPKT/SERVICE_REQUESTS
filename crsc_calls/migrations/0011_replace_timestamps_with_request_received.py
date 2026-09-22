# Replaces ialert_tk_timestamp/mail_rec_timestamp with a single
# request_received_timestamp field. Existing values are backfilled before
# the old columns are dropped — iAlert Ticket Timestamp wins if both were
# set (an iAlert-raised call's timestamp is the more specific of the two).
from django.db import migrations, models


def backfill_request_received_timestamp(apps, schema_editor):
    DirectCall = apps.get_model("crsc_calls", "DirectCall")
    DirectCall.objects.filter(
        request_received_timestamp__isnull=True, ialert_tk_timestamp__isnull=False
    ).update(request_received_timestamp=models.F("ialert_tk_timestamp"))
    DirectCall.objects.filter(
        request_received_timestamp__isnull=True, mail_rec_timestamp__isnull=False
    ).update(request_received_timestamp=models.F("mail_rec_timestamp"))


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crsc_calls", "0010_directcall_darby_lookup_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="directcall",
            name="request_received_timestamp",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Request Received Timestamp"
            ),
        ),
        migrations.RunPython(backfill_request_received_timestamp, noop_reverse),
        migrations.RemoveField(
            model_name="directcall",
            name="ialert_tk_timestamp",
        ),
        migrations.RemoveField(
            model_name="directcall",
            name="mail_rec_timestamp",
        ),
    ]
