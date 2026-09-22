# Backfills Assigned Date on calls created before that field existed
# (added in 0003) — those rows have complaint_assigned_to set but never got
# an assigned_date stamp, so every TAT column stayed blank. Date of
# Complaint is the best available stand-in since no historical assignment
# timestamp was ever recorded for them. Once assigned_date is in place,
# d1_tat/d2_tat/total_tat are computed the same way as
# crsc_calls.services.tat.compute_tats() (duplicated here, not imported, so
# this migration stays correct even if that logic changes later).
from django.db import migrations


def _format_duration(delta):
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def backfill_assigned_date_and_tat(apps, schema_editor):
    DirectCall = apps.get_model("crsc_calls", "DirectCall")
    for call in DirectCall.objects.all():
        changed = False
        if not call.assigned_date and (call.complaint_assigned_to or "").strip():
            call.assigned_date = call.date_of_complaint
            changed = True

        if call.assigned_date:
            if call.date_of_complaint and not call.d1_tat:
                call.d1_tat = _format_duration(call.assigned_date - call.date_of_complaint)
                changed = True
            if call.follow_up_updated_at and not call.d2_tat:
                call.d2_tat = _format_duration(call.follow_up_updated_at - call.assigned_date)
                changed = True
            if call.date_of_closure and not call.total_tat:
                call.total_tat = _format_duration(call.date_of_closure - call.assigned_date)
                changed = True

        if changed:
            call.save(update_fields=["assigned_date", "d1_tat", "d2_tat", "total_tat"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crsc_calls", "0007_alter_directcall_al_updated_contact_no_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_assigned_date_and_tat, noop_reverse),
    ]
