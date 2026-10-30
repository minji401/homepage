class SharedDatabaseRouter:
    """공유 Postgres 테이블에는 Django 마이그레이션 CREATE/DROP을 돌리지 않는다."""

    shared_models = {
        "shareduser",
        "sharedsitecontent",
        "careconsultation",
        "careschedule",
        "product",
        "shopprofile",
        "order",
        "orderitem",
    }

    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.shared_models:
            return "shared"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name in self.shared_models:
            return "shared"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == "shared":
            return False
        if model_name in self.shared_models:
            return False
        return None
