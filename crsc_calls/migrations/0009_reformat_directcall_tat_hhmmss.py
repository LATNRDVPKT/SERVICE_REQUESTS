# Reformats existing d1_tat/d2_tat/total_tat strings from the old
# "Xd Xh Xm" style to HH:MM:SS, matching the updated
# crsc_calls.services.tat.compute_tats() (duplicated here, not imported, so
# this migration stays correct even if that logic changes later). Recomputed
# straight from the same source timestamps rather than parsed out of the old
# strings, since those never stored seconds.
from django.db import migrations


def _format_duration(delta):
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def reformat_tat(apps, schema_editor):
    DirectCall = apps.get_model("crsc_calls", "DirectCall")
    for call in DirectCall.objects.all():
        changed = False
        if call.assigned_date and call.date_of_complaint:
            call.d1_tat = _format_duration(call.assigned_date - call.date_of_complaint)
            changed = True
        if call.assigned_date and call.follow_up_updated_at:
            call.d2_tat = _format_duration(call.follow_up_updated_at - call.assigned_date)
            changed = True
        if call.assigned_date and call.date_of_closure:
            call.total_tat = _format_duration(call.date_of_closure - call.assigned_date)
            changed = True
        if changed:
            call.save(update_fields=["d1_tat", "d2_tat", "total_tat"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crsc_calls", "0008_backfill_directcall_assigned_date_and_tat"),
    ]

    operations = [
        migrations.RunPython(reformat_tat, noop_reverse),
    ]
