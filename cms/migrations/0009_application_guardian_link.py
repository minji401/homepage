import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cms", "0008_storedupload"),
    ]

    operations = [
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
                ],
                default="received",
                max_length=20,
                verbose_name="상태",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="care_applications",
                to=settings.AUTH_USER_MODEL,
                verbose_name="신청 회원",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="patient_id",
            field=models.CharField(blank=True, max_length=80, verbose_name="어르신 프로필 ID"),
        ),
        migrations.AddField(
            model_name="application",
            name="senior_name",
            field=models.CharField(blank=True, max_length=50, verbose_name="대상 어르신"),
        ),
    ]
