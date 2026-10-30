from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0006_application_pii_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="extra_images",
            field=models.JSONField(blank=True, default=list, verbose_name="추가 사진"),
        ),
        migrations.AddField(
            model_name="post",
            name="attachment",
            field=models.CharField(blank=True, max_length=400, verbose_name="첨부파일"),
        ),
        migrations.AddField(
            model_name="post",
            name="attachment_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="첨부파일명"),
        ),
    ]
