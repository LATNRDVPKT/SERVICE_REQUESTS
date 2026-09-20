"""
Creates the project's 14 shared login accounts: 3 admins + 11 engineers.

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
    ("admin1", "Admin One"),
    ("admin2", "Admin Two"),
    ("admin3", "Admin Three"),
]

ENGINEERS = [
    ("engineer1", "Engineer One"),
    ("engineer2", "Engineer Two"),
    ("engineer3", "Engineer Three"),
    ("engineer4", "Engineer Four"),
    ("engineer5", "Engineer Five"),
    ("engineer6", "Engineer Six"),
    ("engineer7", "Engineer Seven"),
    ("engineer8", "Engineer Eight"),
    ("engineer9", "Engineer Nine"),
    ("engineer10", "Engineer Ten"),
    ("engineer11", "Engineer Eleven"),
]


class Command(BaseCommand):
    help = "Seed the 14 shared accounts (3 admin + 11 engineer) used across AIS140 / CRSC Calls / Billing."

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
                user=user, defaults={"role": "admin" if is_staff else "engineer", "display_name": display_name}
            )
            created_rows.append((username, password or "(unchanged)", "Admin" if is_staff else "Engineer"))

        for username, display_name in ADMINS:
            upsert(username, display_name, role="admin", is_staff=True)
        for username, display_name in ENGINEERS:
            upsert(username, display_name, role="engineer", is_staff=False)

        lines = ["username,password,role"] + [",".join(row) for row in created_rows]
        report = "\n".join(lines)

        with open("seeded_credentials.txt", "w") as f:
            f.write(report + "\n")

        self.stdout.write(self.style.SUCCESS("Seeded 14 accounts (3 admin, 11 engineer):"))
        self.stdout.write(report)
        self.stdout.write(self.style.WARNING(
            "\nFull list also written to seeded_credentials.txt — distribute securely, "
            "this file is gitignored and NOT part of the deployed app."
        ))
