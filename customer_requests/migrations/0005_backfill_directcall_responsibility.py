# Backfills Responsibility on existing calls from whichever tracked event
# (follow-up remark vs. AL Updated Contact No) is most recent — same rule as
# crsc_calls.services.latest_update.get_latest_call_update(), duplicated here
# (not imported) so this migration stays correct even if that logic changes
# later.
from django.db import migrations

RESPONSIBILITY_MAP = {
    "CONTACT DETAILS WRONG": "IALERT",
    "CUSTOMER ISSUE - DASHBOARD MODIFICATION": "CUSTOMER",
    "CUSTOMER ISSUE - FUSE": "CUSTOMER",
    "CUSTOMER ISSUE - PHYSICAL DAMAGE": "CUSTOMER",
    "CUSTOMER ISSUE - THIRDPARTY DEVICE": "CUSTOMER",
    "CUSTOMER ISSUE - VEHICLE WIRING": "CUSTOMER",
    "CUSTOMER ISSUE - WATER INGRESS": "IALERT",
    "CUSTOMER NOT ANSWERING": "IALERT",
    "CUSTOMER RESCHEDULING - VEHICLE SUPPORT DATE": "CUSTOMER",
    "DEALER SENT DEVICE FOR SERVICE": "DANLAW",
    "DEVICE DISPATCHED TO WORKSHOP": "DANLAW",
    "iALERT ISSUE": "IALERT",
    "ISSUE RESOLVED": "CLOSED",
    "MONITORING": "DANLAW",
    "NO ISSUE - CUSTOMER COMPLAINT": "IALERT",
    "OUT OF WARRANTY": "CUSTOMER",
    "VEHICLE PHYSICAL SUPPORT - WAITING": "CUSTOMER",
    "VIDEO CALL SUPPORT - WAITING": "CUSTOMER",
    "SIM EXPIRED": "CUSTOMER",
    "DEVICE TO BE SENT FOR REPAIR": "DANLAW",
    "DEVICE TO BE SENT FOR REPLACE": "DANLAW",
    "CANCELLED": "CUSTOMER",
}


def backfill_responsibility(apps, schema_editor):
    DirectCall = apps.get_model("crsc_calls", "DirectCall")
    for call in DirectCall.objects.all():
        candidates = []
        if call.follow_up_remark and call.follow_up_updated_at:
            candidates.append((call.follow_up_updated_at, "follow_up", call.follow_up_remark))
        if call.al_updated_contact_no and call.al_updated_contact_no_updated_at:
            candidates.append((call.al_updated_contact_no_updated_at, "al_updated_contact_no", ""))
        if not candidates:
            continue

        _, source, remark = max(candidates, key=lambda c: c[0])
        if source == "al_updated_contact_no":
            responsibility = "DANLAW"
        else:
            responsibility = RESPONSIBILITY_MAP.get((remark or "").strip().upper(), "")

        if responsibility:
            call.responsibility = responsibility
            call.save(update_fields=["responsibility"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crsc_calls", "0004_directcall_responsibility"),
    ]

    operations = [
        migrations.RunPython(backfill_responsibility, noop_reverse),
    ]
