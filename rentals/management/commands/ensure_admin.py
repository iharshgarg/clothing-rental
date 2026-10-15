import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Creates the initial superuser if it does not already exist."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not username or not password:
            raise CommandError(
                "DJANGO_SUPERUSER_USERNAME and "
                "DJANGO_SUPERUSER_PASSWORD must be set."
            )

        User = get_user_model()

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Created admin user: {username}")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Admin user already exists: {username}")
            )