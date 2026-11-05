from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0007_integration_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("member", "MEMBER"),
                    ("guardian", "보호자"),
                    ("staff", "STAFF"),
                    ("admin", "ADMIN"),
                ],
                default="member",
                max_length=20,
                verbose_name="권한",
            ),
        ),
        migrations.CreateModel(
            name="SeniorProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shared_user_id", models.CharField(blank=True, max_length=80, verbose_name="공유 회원 ID")),
                ("name", models.CharField(max_length=50, verbose_name="어르신 성함")),
                (
                    "relationship",
                    models.CharField(
                        choices=[
                            ("부", "부"),
                            ("모", "모"),
                            ("조부모", "조부모"),
                            ("배우자", "배우자"),
                            ("자녀", "자녀"),
                            ("기타", "기타"),
                        ],
                        default="기타",
                        max_length=30,
                        verbose_name="보호자와의 관계",
                    ),
                ),
                ("birth_date", models.DateField(blank=True, null=True, verbose_name="생년월일")),
                (
                    "care_grade",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("1등급", "1등급"),
                            ("2등급", "2등급"),
                            ("3등급", "3등급"),
                            ("4등급", "4등급"),
                            ("5등급", "5등급"),
                            ("인지지원등급", "인지지원등급"),
                            ("등급외/신청중", "등급외/신청중"),
                            ("해당없음", "해당없음"),
                        ],
                        max_length=20,
                        verbose_name="장기요양등급",
                    ),
                ),
                ("note", models.TextField(blank=True, verbose_name="특이사항")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "guardian",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="patients",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="보호자",
                    ),
                ),
            ],
            options={
                "verbose_name": "어르신 프로필",
                "verbose_name_plural": "어르신 프로필",
                "db_table": "senior_profiles",
                "ordering": ["-updated_at", "-id"],
            },
        ),
    ]
