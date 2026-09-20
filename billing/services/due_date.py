# =============================================================================
# billing — services/due_date.py
# Theoretical payment due-date rule, taken directly from the original
# calculate_theoretical_payment_due_date() / BillingData.save().
# =============================================================================
from datetime import timedelta

HARDWARE_LOCATIONS_52_DAYS = {"Chennai", "Ennore", "Hosur", "Hosur 1", "Hosur 2", "VVC"}
HARDWARE_LOCATIONS_55_DAYS = {"Pant Nagar", "Alwar"}


def calculate_theoretical_payment_due_date(invoice_date, location, item_sub_category):
    """Business rule for the theoretical payment due date, by location + item category."""
    if not invoice_date or not location or not item_sub_category:
        return None

    loc = (location or "").strip()
    item = (item_sub_category or "").strip()

    if loc == "ALCOB" and item == "Hardware":
        days = 18
    elif item == "Software":
        days = 17
    elif item == "SIM":
        days = 32
    elif item == "NRE":
        days = 17
    elif loc in HARDWARE_LOCATIONS_52_DAYS and item == "Hardware":
        days = 52
    elif loc in HARDWARE_LOCATIONS_55_DAYS and item == "Hardware":
        days = 55
    else:
        days = 0

    return invoice_date + timedelta(days=days) if days else None


# (customer_name, location) -> (due_emails, shipment_emails), semicolon-
# separated strings. Fill in your own customer/location combinations —
# left empty by default.
EMAIL_MAPPING = {
    # ("Switch", "Chennai"): ("due1@example.com;due2@example.com", "ship1@example.com"),
}
