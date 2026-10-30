from django.core.management.base import BaseCommand
from django.db.utils import OperationalError, ProgrammingError

from accounts.shared_schema import ensure_integration_schema
from accounts.shared_users import ensure_shared_schema, shared_enabled


class Command(BaseCommand):
    help = "공유 Postgres 테이블을 migrate 이후에 만듭니다. 테이블이 없으면 배포를 중단하지 않습니다."

    def handle(self, *args, **options):
        if not shared_enabled():
            self.stdout.write("shared db: DATABASE_URL 없음, 건너뜀")
            return
        try:
            ensure_shared_schema()
            ensure_integration_schema()
        except (OperationalError, ProgrammingError):
            self.stdout.write("shared schema: 테이블이 아직 없어 건너뜀")
            return
        self.stdout.write("shared schema: ok")
