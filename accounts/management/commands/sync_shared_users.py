from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from accounts.models import SharedUser
from accounts.scrypt_compat import hash_password
from accounts.shared_users import (
    get_shared_by_phone,
    mark_herium_linked,
    normalize_phone,
    shared_enabled,
)
from datetime import datetime, timezone
from uuid import uuid4


class Command(BaseCommand):
    help = (
        "헤리움 SQLite 회원을 phone 기준으로 공유 users 테이블에 이전합니다. "
        "기존 Django 비밀번호(PBKDF2)는 scrypt로 바꿀 수 없어, "
        "이전에만 넣은 계정은 비밀번호 재설정 또는 한 번 로그인이 필요합니다."
    )

    def handle(self, *args, **options):
        if not shared_enabled():
            raise CommandError("DATABASE_URL(또는 SHARED_DATABASE_URL)이 없어 공유 DB에 연결할 수 없습니다.")

        created = 0
        linked = 0
        skipped = 0
        reset_needed = []
        seed_usernames = {"admin", "hatsal", "parkmin", "leeguard"}

        for user in User.objects.select_related("profile").order_by("id"):
            if user.username in seed_usernames:
                skipped += 1
                self.stdout.write(f"skip  {user.username}: 예시 계정")
                continue
            profile = getattr(user, "profile", None)
            digits = normalize_phone(profile.phone if profile else "")
            if not digits:
                skipped += 1
                self.stdout.write(f"skip  {user.username}: 연락처 없음")
                continue

            shared = get_shared_by_phone(digits)
            if shared is not None:
                mark_herium_linked(shared, note=f"herium_username={user.username}", username=user.username)
                linked += 1
                continue

            SharedUser(
                id=f"u_{uuid4()}",
                name="",
                phone=digits,
                username=user.username,
                guardian_name=(profile.name if profile and profile.name else user.first_name) or user.username,
                password_hash=hash_password(f"reset-required-{uuid4()}"),
                role="admin" if (user.is_staff or (profile and profile.role == "admin")) else "user",
                herium_linked=1,
                herium_relation=None,
                herium_note=f"herium_username={user.username};password_reset_required=1",
                created_at=datetime.now(timezone.utc).isoformat(),
            ).save(using="shared", force_insert=True)
            created += 1
            reset_needed.append(f"{user.username} / {digits}")

        self.stdout.write(self.style.SUCCESS(
            f"완료: 신규 {created}, 기존 연결 {linked}, 연락처 없음 {skipped}"
        ))
        if reset_needed:
            self.stdout.write(self.style.WARNING(
                "아래 계정은 공유 DB에 넣었지만 기존 비밀번호를 검증할 수 없습니다. "
                "헤리움에서 한 번 로그인하거나 비밀번호 찾기로 재설정해야 현대 의료기에서도 같은 비밀번호를 쓸 수 있습니다."
            ))
            for item in reset_needed:
                self.stdout.write(f"  - {item}")
