from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import SharedUser
from accounts.shared_users import ensure_shared_schema, shared_enabled, shared_expected


class Command(BaseCommand):
    help = "공유 users 연결만 확인하고 URL/비밀번호는 출력하지 않습니다."

    def handle(self, *args, **options):
        if not shared_enabled():
            if shared_expected():
                self.stderr.write("shared db: DATABASE_URL set but not parsed")
            else:
                self.stderr.write("shared db: not configured")
            return

        cfg = settings.DATABASES["shared"]
        engine = cfg.get("ENGINE", "")
        if "postgresql" in engine:
            self.stdout.write(
                "shared postgres: configured "
                f"name={cfg.get('NAME')} host_set={'yes' if cfg.get('HOST') else 'no'}"
            )
        else:
            self.stdout.write(f"shared sqlite: configured name={cfg.get('NAME')}")
        try:
            ensure_shared_schema()
            count = SharedUser.objects.using("shared").count()
            latest = SharedUser.objects.using("shared").order_by("-created_at").first()
            self.stdout.write(f"users table: ok count={count}")
            if latest:
                phone = latest.phone or ""
                hashed = latest.password_hash or ""
                self.stdout.write(
                    f"users latest: phone_prefix={phone[:3]} hash_prefix={hashed[:8]}"
                )
        except Exception as exc:
            self.stderr.write(f"users table: ERROR {type(exc).__name__}: {exc}")
            raise
