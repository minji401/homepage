from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0003_popup_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="UsageStat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True, verbose_name="코드")),
                ("name", models.CharField(max_length=80, verbose_name="구분명")),
                ("capacity", models.PositiveIntegerField(default=0, verbose_name="정원")),
                ("current", models.PositiveIntegerField(default=0, verbose_name="현원")),
                ("waiting", models.PositiveIntegerField(default=0, verbose_name="대기 인원")),
                ("general_capacity", models.PositiveIntegerField(default=0, verbose_name="일반실 정원")),
                ("dementia_capacity", models.PositiveIntegerField(default=0, verbose_name="치매전담실 정원")),
                ("sort_order", models.PositiveIntegerField(default=1, verbose_name="순서")),
            ],
            options={
                "verbose_name": "이용 현황",
                "verbose_name_plural": "이용 현황",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="WaitlistEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=40, verbose_name="성명")),
                ("service_type", models.CharField(max_length=40, verbose_name="구분")),
                ("queue_no", models.PositiveIntegerField(verbose_name="대기 순번")),
            ],
            options={
                "verbose_name": "대기자",
                "verbose_name_plural": "대기자 명단",
                "ordering": ["service_type", "queue_no", "id"],
            },
        ),
    ]
