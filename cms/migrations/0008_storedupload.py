from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0007_post_images_attachment"),
    ]

    operations = [
        migrations.CreateModel(
            name="StoredUpload",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("folder", models.CharField(default="posts", max_length=40)),
                ("filename", models.CharField(max_length=200)),
                ("content_type", models.CharField(default="application/octet-stream", max_length=120)),
                ("data", models.BinaryField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
    ]
