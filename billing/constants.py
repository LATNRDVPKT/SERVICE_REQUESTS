# =============================================================================
# billing — constants.py
# Curated suggestion lists for the invoice form — these are plain CharFields
# (not model choices) so any value can still be typed; these lists just
# drive the <datalist> quick-pick suggestions, same values as the original
# hand-built <select> option lists.
# =============================================================================
CUSTOMER_NAME_SUGGESTIONS = [
    "Ashok Leyland Limited", "Switch", "Surin", "Prabha", "Royal Enfield",
    "SMS", "NeelMetal", "Ohm Global Mobility",
]

LOCATION_SUGGESTIONS = [
    "Pant Nagar", "Alwar", "ALCOB", "Chennai", "Ennore", "Hosur",
    "Hosur 1", "Hosur 2", "Hosur SPD", "VVC", "Bangalore",
]

PART_NO_SUGGESTIONS = [
    "BHG00433", "BHG00435", "XIV01900", "F3V06900", "F3V07000",
    "RAM00257/A", "RAM00311/A", "P6M00148", "FZS01400", "SC", "BC",
    "Esim Charges", "Cloud charges", "S/W services", "BSEXT",
    "Single to Dual", "Data Porting", "Data Porting-GS",
    "AIS140 - Data Porting", "S-Flag", "AIS140SC", "Debit Note",
    "DL548-Reworked device", "DL545-Reworked device",
    "SIM replacement device", "SIM-M&HCV", "SIM-LCV", "SIM-Genset",
    "Data porting-M&HCV", "Data porting-LCV", "Data porting-Genset",
    "SIM Replacement Services",
]

PRODUCT_SUGGESTIONS = ["Darby", "NRE", "SIM Subscription", "TCU", "Akteena"]

CATEGORY_SUGGESTIONS = [
    "A.L TCU", "SaaS", "eSIM", "SLD ConnectALL", "Engg NRE", "A.L VCU",
    "AIS 140SC", "R.E TCU", "ADAS Camera",
]

PART_SUB_CATEGORY_SUGGESTIONS = [
    "DL548", "DL545", "DL310", "Genset", "VCU", "LCV", "Dongle",
    "SLD ConnectALL", "Data porting", "SIM billing", "NRE", "S-Flag",
    "B.S Extension", "Single to Dual", "PD billing",
    "AIS 140 - Data porting", "AIS 140 SIM charges",
    "AIS 140 Service charges", "ADAS Camera",
]

# item_sub_category drives the due-date rules; those rules match it
# case-insensitively (see services/due_date.py), so typed values are safe.
ITEM_SUB_CATEGORY_SUGGESTIONS = ["Software", "Hardware", "SIM", "BC", "NRE"]
