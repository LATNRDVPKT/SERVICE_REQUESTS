"""
Creates 30 additional shared logins: 7 managers + 23 engineers.

Usage:
    python manage.py seed_team_logins
    python manage.py seed_team_logins --reset-passwords   # fresh passwords for existing ones too

"Manager" access means profile.role == "admin" (Part-A / new-call forms,
admin-only screens, FIR statuses, HOD comment). These accounts are NOT
Django-admin staff/superusers, so they can't open /admin/.

Usernames and generated passwords are written to team_credentials.txt in
the project root (gitignored — never commit it). Existing accounts are left
untouched unless --reset-passwords is given.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from accounts.models import UserProfile

MANAGER_COUNT = 7
ENGINEER_COUNT = 23
PASSWORD_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


class Command(BaseCommand):
    help = "Create 30 logins: 7 manager (admin role) + 23 engineer."

    def add_arguments(self, parser):
        parser.add_argument("--reset-passwords", action="store_true",
                            help="Generate a fresh password even for accounts that already exist.")

    def handle(self, *args, **options):
        reset = options["reset_passwords"]
        rows = []

        def upsert(username, display_name, role):
            user, is_new = User.objects.get_or_create(
                username=username, defaults={"is_staff": False, "is_superuser": False}
            )
            password = None
            if is_new or reset:
                password = get_random_string(12, allowed_chars=PASSWORD_CHARS)
                user.set_password(password)
                user.save()
            UserProfile.objects.update_or_create(
                user=user, defaults={"role": role, "display_name": display_name}
            )
            rows.append((username, password or "(unchanged)", "Manager" if role == "admin" else "Engineer"))

        for n in range(1, MANAGER_COUNT + 1):
            upsert(f"manager_{n:02d}", f"Manager {n:02d}", "admin")
        for n in range(1, ENGINEER_COUNT + 1):
            upsert(f"engineer_{n:02d}", f"Engineer {n:02d}", "engineer")

        with open("team_credentials.txt", "w", encoding="utf-8") as fh:
            fh.write("username,password,role\n")
            fh.write("\n".join(",".join(r) for r in rows) + "\n")

        self.stdout.write(self.style.SUCCESS(
            f"{len(rows)} logins ready ({MANAGER_COUNT} manager, {ENGINEER_COUNT} engineer)."
        ))
        self.stdout.write(self.style.WARNING(
            "Credentials written to team_credentials.txt (gitignored) — distribute securely."
        ))
