from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile


class Command(BaseCommand):
    help = "데모 계정 hatsal / 1234 을 만듭니다."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username="hatsal",
            defaults={
                "first_name": "홍길동",
                "email": "hatsal@example.com",
            },
        )
        if created:
            user.set_password("1234")
            user.save()
        Profile.objects.update_or_create(
            user=user,
            defaults={
                "name": "홍길동",
                "phone": "010-1234-5678",
            },
        )
        self.stdout.write(self.style.SUCCESS("데모 계정 준비: hatsal / 1234"))
