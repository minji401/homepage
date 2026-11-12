from django.db import migrations, models


def add_cancel_columns(apps, schema_editor):
    table = "cms_application"
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        try:
            existing = {col.name for col in connection.introspection.get_table_description(cursor, table)}
        except Exception:
            return
        if "cancel_reason" not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN cancel_reason text NULL")
        if "cancelled_at" not in existing:
            stamp = "timestamp with time zone NULL" if connection.vendor == "postgresql" else "datetime NULL"
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN cancelled_at {stamp}")


def noop(_apps, _schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0009_application_guardian_link"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="application",
                    name="cancel_reason",
                    field=models.TextField(blank=True, null=True, verbose_name="취소 사유"),
                ),
                migrations.AddField(
                    model_name="application",
                    name="cancelled_at",
                    field=models.DateTimeField(blank=True, null=True, verbose_name="취소 일시"),
                ),
                migrations.AlterField(
                    model_name="application",
                    name="status",
                    field=models.CharField(
                        choices=[
                            ("received", "접수완료"),
                            ("waiting", "상담대기"),
                            ("done", "상담완료"),
                            ("approved", "승인"),
                            ("rejected", "반려"),
                            ("CANCELLED", "취소됨"),
                        ],
                        default="received",
                        max_length=20,
                        verbose_name="상태",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_cancel_columns, noop),
            ],
        ),
    ]
