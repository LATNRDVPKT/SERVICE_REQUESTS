"""
Creates the project's shared login accounts: admins, engineers, plants and finance.

Usage:
    python manage.py seed_users
    python manage.py seed_users --reset-passwords   # generate fresh passwords for existing users too

Every account's username and a freshly generated password are printed to
the terminal and also written to seeded_credentials.txt in the project
root (already in .gitignore — never commit this file). Distribute the
credentials securely and have each person change their password after
first login (python manage.py changepassword <username>, or via /admin/).
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from accounts.models import UserProfile

ADMINS = [
    ("upendra", "Upendra"),
    ("gowtham", "Gowtham"),
    ("manager", "Manager"),
]

# Plant logins — each sees only the CRSC calls whose "Faulty Device Sent to
# Location" is their plant, and only the plant fields.
PLANTS = [
    ("plant_hyderabad", "Hyderabad Plant", "Hyderabad"),
    ("plant_goa", "Goa Plant", "Goa"),
]

# Finance logins — can open only the Billing module.
FINANCE = [
    ("cfo", "CFO"),
    ("gowtham_finance", "Gowtham (Finance)"),
    ("manager_finance", "Manager (Finance)"),
]

ENGINEERS = [
    ("eliyas", "Eliyas"),
    ("gayadhar", "Gayadhar"),
    ("jitendra", "Jitendra"),
    ("paribesh", "Paribesh"),
    ("dilip_kumar", "Dilip Kumar"),
    ("yoga", "Yoga"),
    ("narendra", "Narendra"),
    ("dimple", "Dimple"),
    ("siva", "Siva"),
    ("omendra", "Omendra"),
    ("manish", "Manish"),
    ("swamy", "Swamy"),
    ("janam", "Janam"),
]


class Command(BaseCommand):
    help = "Seed the shared login accounts (admin, engineer, plant, finance)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords", action="store_true",
            help="Generate and set a fresh password even for accounts that already exist.",
        )

    def handle(self, *args, **options):
        reset = options["reset_passwords"]
        created_rows = []

        def upsert(username, display_name, role, is_staff):
            user, is_new = User.objects.get_or_create(
                username=username, defaults={"is_staff": is_staff, "is_superuser": is_staff}
            )
            password = None
            if is_new or reset:
                password = get_random_string(
                    12, allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
                )
                user.set_password(password)
                user.is_staff = is_staff
                user.is_superuser = is_staff
                user.save()
            UserProfile.objects.update_or_create(
                user=user, defaults={"role": role, "display_name": display_name}
            )
            created_rows.append((username, password or "(unchanged)", role.capitalize()))

        for username, display_name in ADMINS:
            upsert(username, display_name, role="admin", is_staff=True)
        for username, display_name in ENGINEERS:
            upsert(username, display_name, role="engineer", is_staff=False)
        for username, display_name in FINANCE:
            upsert(username, display_name, role="finance", is_staff=False)

        for username, display_name, location in PLANTS:
            user, is_new = User.objects.get_or_create(username=username)
            password = None
            if is_new or reset:
                password = get_random_string(
                    12, allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
                )
                user.set_password(password)
                user.is_staff = False
                user.is_superuser = False
                user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": "plant", "display_name": display_name, "plant_location": location},
            )
            created_rows.append((username, password or "(unchanged)", f"Plant - {location}"))

        lines = ["username,password,role"] + [",".join(row) for row in created_rows]
        report = "\n".join(lines)

        with open("seeded_credentials.txt", "w") as f:
            f.write(report + "\n")

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created_rows)} accounts:"))
        self.stdout.write(report)
        self.stdout.write(self.style.WARNING(
            "\nFull list also written to seeded_credentials.txt — distribute securely, "
            "this file is gitignored and NOT part of the deployed app."
        ))
