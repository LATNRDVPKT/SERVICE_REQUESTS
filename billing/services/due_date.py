# =============================================================================
# billing — services/due_date.py
# Theoretical payment due-date rule, taken directly from the original
# calculate_theoretical_payment_due_date() / BillingData.save().
# =============================================================================
from datetime import timedelta

HARDWARE_LOCATIONS_52_DAYS = {"chennai", "ennore", "hosur", "hosur 1", "hosur 2", "vvc"}
HARDWARE_LOCATIONS_55_DAYS = {"pant nagar", "alwar"}


def calculate_theoretical_payment_due_date(invoice_date, location, item_sub_category):
    """Business rule for the theoretical payment due date, by location + item category.
    Matching is case-insensitive so typed values like 'hardware' still count."""
    if not invoice_date or not location or not item_sub_category:
        return None

    loc = (location or "").strip().lower()
    item = (item_sub_category or "").strip().lower()

    if loc == "alcob" and item == "hardware":
        days = 18
    elif item == "software":
        days = 17
    elif item == "sim":
        days = 32
    elif item == "nre":
        days = 17
    elif loc in HARDWARE_LOCATIONS_52_DAYS and item == "hardware":
        days = 52
    elif loc in HARDWARE_LOCATIONS_55_DAYS and item == "hardware":
        days = 55
    else:
        days = 0

    return invoice_date + timedelta(days=days) if days else None


# (customer_name, location) -> (due_emails, shipment_emails), semicolon-
# separated strings.
EMAIL_MAPPING = {
    ("Switch", "Chennai"): (
        "Lakshmanan.p@switchmobilityev.com;karthikpandy.p@switchmobilityev.com;gayadharm@danlawtech.com;rishwanthr@danlawtech.com",
        "Lakshmanan.p@switchmobilityev.com;karthikpandy.p@switchmobilityev.com;gayadharm@danlawtech.com;rishwanthr@danlawtech.com",
    ),
    ("Switch", "Hosur"): (
        "Lakshmanan.p@switchmobilityev.com;karthikpandy.p@switchmobilityev.com;eliyasp@danlawtech.com",
        "Lakshmanan.p@switchmobilityev.com;karthikpandy.p@switchmobilityev.com;eliyasp@danlawtech.com",
    ),
    ("Surin", "Chennai"): (
        "accounts2.chennai@surinauto.com;purchase3.chennai@surinauto.com;accounts2.pkm@surinauto.com;rishwanthr@danlawtech.com",
        "purchase3.chennai@surinauto.com;rishwanthr@danlawtech.com",
    ),
    ("Surin", "Pant Nagar"): (
        "accounts4.utk@surinauto.com;prakash.kandpal@surinauto.com;mr.utk@surinauto.com;dheeresh@surinauto.com;gayadharm@danlawtech.com",
        "prakash.kandpal@surinauto.com;gayadharm@danlawtech.com;mr.utk@surinauto.com",
    ),
    ("Prabha", "Chennai"): (
        "munusamy.s@prabhaengineers.com;ganesh.r@prabhaengineers.com;rishwanthr@danlawtech.com",
        "munusamy.s@prabhaengineers.com;srikanth.n@prabhaengineers.com;rishwanthr@danlawtech.com",
    ),
    ("Prabha", "Hosur"): (
        "balamurugan@prabhaengineers.com;sankar.s@prabhaengineers.com;eliyasp@danlawtech.com",
        "balamurugan@prabhaengineers.com;eliyasp@danlawtech.com",
    ),
    ("Prabha", "Pant Nagar"): (
        "jeevan.singh@prabhaengineers.com;ankit@prabhaengineers.com;gayadharm@danlawtech.com",
        "ankit@prabhaengineers.com;gayadharm@danlawtech.com",
    ),
    ("NeelMetal", "Pant Nagar"): (
        "dinesh.satyawali@jbmgroup.com;manoj.joshi@jbmgroup.com;gayadharm@danlawtech.com",
        "janam.singh@jbmgroup.com;n10b.purchase@jbmgroup.com;gayadharm@danlawtech.com",
    ),
    ("Motherson", "Chennai"): (
        "balagopal.mathivanan@motherson.com;varadarajan.narayanan@motherson.com;rishwanthr@danlawtech.com",
        "varadarajan.narayanan@motherson.com;rishwanthr@danlawtech.com",
    ),
    ("SMS", "Chennai"): (
        "sales@smsautoline.in;rishwanthr@danlawtech.com",
        "sales@smsautoline.in;rishwanthr@danlawtech.com",
    ),
}

# Days to add to the Actual GRN/Delivery Date to get the real due_date, by
# (customer_name, item_sub_category) — distinct from the theoretical rule
# above, which is based on invoice_date + location/item instead.
GRN_DUE_DATE_RULES = {
    ("ashok leyland limited", "hardware"): 45,
    ("switch", "hardware"): 45,
    ("ashok leyland limited", "software"): 15,
    ("royal enfield", "hardware"): 45,
    ("ashok leyland limited", "sim"): 15,
    ("ashok leyland limited", "nre"): 30,
}


def calculate_due_date(customer_name, item_sub_category, grn_date, theoretical_due_date=None):
    """Real due_date rule: customer/item-specific days added to the Actual
    GRN/Delivery Date. Falls back to the theoretical_payment_due_date when
    no GRN date is set yet, or no rule matches this customer/item — same
    behaviour as the original client-side calculateDueDate()."""
    if not grn_date:
        return None

    key = ((customer_name or "").strip().lower(), (item_sub_category or "").strip().lower())
    days = GRN_DUE_DATE_RULES.get(key)
    if days:
        return grn_date + timedelta(days=days)
    return theoretical_due_date
