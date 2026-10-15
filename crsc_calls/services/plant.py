# =============================================================================
# crsc_calls — services/plant.py
# What the plant logins (Hyderabad / Goa) see and may edit.
# =============================================================================
PLANT_LOCATIONS = ("Hyderabad", "Goa")

# Shown read-only on the plant form and as the first columns of the plant
# dashboard / download — (model field, label).
PLANT_READONLY_FIELDS = [
    ("unique_id", "Unique ID"),
    ("psn", "Faulty Device PSN Number"),
    ("vin", "VIN"),
    ("complaint_assigned_to", "Engineer Responsible"),
    ("device_IMEI", "Device IMEI"),
    ("device_ICCID", "Device ICCID"),
    ("chargable_or_not", "Chargeable or Not"),
    ("payment_status", "Payment Status"),
    ("issue_identified", "Issue Identified"),
    ("device_to_be_sent", "Faulty Device Sent to Location"),
    ("hod_comment", "HOD Comment"),
    ("dealer_address", "Dealer Address"),
    ("rr_responsibility", "RR Responsibility"),
]

# The only fields a plant login can edit.
PLANT_EDIT_FIELDS = [
    ("copq_labour", "CoPQ Labour"),
    ("copq_material", "CoPQ Material"),
    ("materials_used", "Materials Used"),
    ("plant_analysis", "Plant Analysis"),
    ("plant_conclusion", "Plant Conclusion"),
    ("device_shipped_date", "Device Shipped Date"),
    ("device_shipped_through", "Device Shipped Through"),
    ("device_shipped_lr_no", "Device Shipped LR No"),
    ("new_device_serial_no", "Repaired/New Device Serial No"),
    ("plant_status", "Plant Status"),

]

# Required once Plant Status is set to Closed.
PLANT_REQUIRED_WHEN_CLOSED = [
    "copq_labour", "copq_material", "materials_used", "plant_analysis", "plant_conclusion",
    "device_shipped_date", "device_shipped_through", "device_shipped_lr_no",
    "plant_status"
]

PLANT_COLUMNS = [    ("unique_id", "Unique ID"),
    ("psn", "Faulty Device PSN Number"),
    ("new_device_serial_no", "Repaired/New Device Serial No"),

    ("vin", "VIN"),
    ("complaint_assigned_to", "Engineer Responsible"),
    ("plant_status", "Plant Status"),
    ("rr_responsibility", "RR Responsibility"),
    ("device_IMEI", "Device IMEI"),
    ("device_ICCID", "Device ICCID"),
    ("chargable_or_not", "Chargeable or Not"),
    ("payment_status", "Payment Status"),
    ("issue_identified", "Issue Identified"),
    ("device_to_be_sent", "Faulty Device Sent to Location"),
    ("hod_comment", "HOD Comment"),
    ("dealer_address", "Dealer Address"),
        ("copq_labour", "CoPQ Labour"),
    ("copq_material", "CoPQ Material"),
    ("materials_used", "Materials Used"),
    ("plant_analysis", "Plant Analysis"),
    ("plant_conclusion", "Plant Conclusion"),
    ("device_shipped_date", "Device Shipped Date"),
    ("device_shipped_through", "Device Shipped Through"),
    ("device_shipped_lr_no", "Device Shipped LR No"),
    ]
PLANT_EDIT_KEYS = [key for key, _ in PLANT_EDIT_FIELDS]
PLANT_LABELS = dict(PLANT_EDIT_FIELDS)
