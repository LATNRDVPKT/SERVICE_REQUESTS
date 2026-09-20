# =============================================================================
# crsc_calls — services/latest_update.py
# Dashboard "what's the most recent thing that happened on this call"
# engine — same shape as AIS140's get_latest_ticket_update().
# =============================================================================
from crsc_calls.constants import get_responsibility


def get_latest_call_update(call):
    candidates = []
    if call.follow_up_remark and call.follow_up_updated_at:
        candidates.append((call.follow_up_updated_at, "follow_up", call.follow_up_remark, call.follow_up_comment or ""))
    if call.al_updated_contact_no and call.al_updated_contact_no_updated_at:
        candidates.append((call.al_updated_contact_no_updated_at, "al_updated_contact_no",
                            call.al_updated_contact_no, ""))

    if not candidates:
        return {"remark": "", "comment": "", "updated_at": None, "responsibility": "",
                "next_follow_up_exp_date": call.next_follow_up_exp_date}

    updated_at, source, remark, comment = max(candidates, key=lambda c: c[0])
    return {
        "remark": remark,
        "comment": comment,
        "updated_at": updated_at,
        "responsibility": get_responsibility(source, remark),
        "next_follow_up_exp_date": call.next_follow_up_exp_date,
    }
