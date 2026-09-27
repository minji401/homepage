from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0005_dailymenu"),
    ]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="name",
            field=models.TextField(verbose_name="이름"),
        ),
        migrations.AlterField(
            model_name="application",
            name="phone",
            field=models.TextField(verbose_name="연락처"),
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor", models.CharField(max_length=80)),
                ("action", models.CharField(max_length=80)),
                ("target", models.CharField(blank=True, max_length=120)),
                ("ip", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
