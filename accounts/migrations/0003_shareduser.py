from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_profile_role_profile_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="SharedUser",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("phone", models.TextField(unique=True)),
                ("password_hash", models.TextField()),
                ("role", models.TextField(default="user")),
                ("herium_linked", models.IntegerField(default=0)),
                ("herium_relation", models.TextField(blank=True, null=True)),
                ("herium_note", models.TextField(blank=True, null=True)),
                ("created_at", models.TextField()),
            ],
            options={
                "verbose_name": "공유 회원",
                "verbose_name_plural": "공유 회원",
                "db_table": "users",
                "managed": False,
            },
        ),
    ]
