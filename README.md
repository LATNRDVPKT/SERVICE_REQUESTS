# Service Requests — Django Project

One project, one shared login, three workflow modules:

| Module | URL prefix | Who can access it |
|---|---|---|
| **AIS140** | `/ais140/` | Any logged-in user |
| **CRSC Calls** | `/crsc/` | Any logged-in user |
| **Billing** | `/billing/` | Admin accounts only |

## 1. Prerequisites

- Python 3.11+
- MySQL 8.x (or MariaDB 10.6+)
- An SMTP account
- `virtualenv` recommended

Linux (Ubuntu/Debian) build deps for `mysqlclient`:
```bash
sudo apt-get update
sudo apt-get install -y build-essential default-libmysqlclient-dev pkg-config
```
Windows: prebuilt wheels usually work with plain `pip install`; if not, see the
`pymysql` fallback described in the AIS140-only README this project grew from.

## 2. Set up

```bash
cd service_requests
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: DB_*, EMAIL_*, IALERT_*, DARBY_* — see the file for every key
```

Create the MySQL database and user:
```sql
CREATE DATABASE service_requests_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sr_user'@'localhost' IDENTIFIED BY 'UPENdra@4G1';
GRANT ALL PRIVILEGES ON service_requests_db.* TO 'sr_user'@'localhost';
FLUSH PRIVILEGES;
```

## 3. Migrate and seed the 14 accounts

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_users
```

`seed_users` creates:
- **3 admin accounts**: `admin1`, `admin2`, `admin3` — full access, including Billing
- **11 engineer accounts**: `engineer1` … `engineer11` — AIS140 + CRSC Calls only

Every username and a freshly generated password are printed to the terminal
**and** written to `seeded_credentials.txt` in the project root (already
gitignored — never commit it). Distribute the credentials securely and have
each person change their password after first login. To rename anyone or
adjust who's an engineer vs admin, edit `accounts/management/commands/seed_users.py`
and re-run with `--reset-passwords`, or just edit `UserProfile` rows directly
in `/admin/`.

Rename the placeholder display names ("Engineer One", "Admin Two", etc.) to
real people any time — that's exactly why engineer/assignee fields across all
three apps pull from `UserProfile.display_name` instead of free-typed e-mails.

## 4. Run it

```bash

python manage.py runserver
```

Open `http://127.0.0.1:8000/` — you'll land on the login page, then the
module-picker home page. `/admin/` is the Django admin (admin accounts only).

## 5. What's implemented in each module

### AIS140 (`/ais140/`)
Full certification-ticket lifecycle: Part-A intake (6 mandatory fields with
inline validation), Part-B resolution with a **remarks dropdown** (auto-maps
to a suggested comment — editable), automatic `Update_to_AL_API` derivation,
Darby auto-lookup on ticket creation, iAlert push for API-originated tickets,
a **live-filtering** Real-Time dashboard (no page reload) with Request/
Completion date-range filters, and three charts: Requests Received /
Completed cards (completion rule: Karnataka, Tamil Nadu & Himachal Pradesh
count "Temporary" as complete; every other state counts "Permanent"), a
state-wise received-vs-completed bar chart, and an engineer-wise completed-
tickets pie chart. A selectable-column CSV export replaces the old two-button
download.

### CRSC Calls (`/crsc/`)
Grounded in the original `DirectCall` model. Part-A intake with VIN
(17-char), PSN (10-digit) and contact-number validators, an "Others" option
on the dropdown fields. Part-B replaces the old separate D1/D2/D3 field sets
with **one unified follow-up block** (remark / comment / engineer / closure
date), auto-locked once submitted, with `next_follow_up_exp_date`
auto-sequenced for iAlert calls (D1 → D2 is +2 days, D2 → D3 is +3 more
days). Remarks are a fixed selectable list (+4 extra remarks only offered
for `direct_call`), each auto-mapping to a suggested comment. FIR sub-fields
become mandatory when Call Status is "FIR - For approval"; the three FIR
closure statuses (Repair/Replace/Replace_Repair) and the HOD Comment field
are only shown to admin accounts. The Real-Time dashboard has date-range,
status, call-type, engineer and ticket-number filters plus a **VIN/PSN
typeahead** that only starts filtering once 5+ characters are typed, and
Received/Closed/Pending cards with status and engineer charts.

### Billing (`/billing/`)
`BillingData`/`OrderDetail`, admin-only end to end. The theoretical
payment-due-date calculation and customer/location email-mapping logic are
carried over exactly from the original `calculate_theoretical_payment_due_date`.
Every invoice row has an **eye icon** opening a field-level change history —
old value struck through in red, new value in green, who changed it and
when — powered by a new `BillingDataHistory` audit table, diffed
automatically on every save.

## 6. Charts run on a locally-vendored Chart.js

`static/vendor/chart.umd.min.js` ships with the project — no CDN dependency,
so the dashboards work on a fully offline/intranet deployment too. If you
ever want to upgrade the version, download a newer `chart.umd.min.js` build
and replace that one file.

## 7. Scope note — what's deliberately not built yet

CRSC Calls' deeper device-repair / alternate-device / shipment-tracking
sub-module (the original `device_repair_form`, `alt_device_form`,
`device_tracking*`, `part_e_form`, `part_f_form` views), Celery-based async
PDF generation, and the full pandas/xlsxwriter pivot Excel report in Billing
were intentionally left out of this pass so what's shipped could be properly
tested end to end rather than guessed at. The model/service layering
(`services/` folders in each app) is built so these can be added without
touching the core workflow logic.

## 8. Project layout

```
service_requests/
    manage.py
    requirements.txt
    .env.example
    service_requests/       # Django project settings, urls
    core/                   # shared base template, home page, admin_required decorator
    accounts/                # UserProfile, seed_users command, login
    AIS140_FLOW/              # AIS140 module
    crsc_calls/               # CRSC Calls module
    billing/                  # Billing module (admin-only)
    templates/base.html       # shared layout every app extends
    static/css/style.css      # shared styling
    static/js/app.js          # shared history-modal / live-filter / autofill / lock-confirm JS
    static/vendor/chart.umd.min.js
```
