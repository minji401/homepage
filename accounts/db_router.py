class SharedDatabaseRouter:
    """공유 Postgres(users)에는 Django 마이그레이션을 돌리지 않는다."""

    shared_model = "shareduser"

    def db_for_read(self, model, **hints):
        if model._meta.model_name == self.shared_model:
            return "shared"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name == self.shared_model:
            return "shared"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "shared":
            return False
        if model_name == self.shared_model:
            return False
        return None
