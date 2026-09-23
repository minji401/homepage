from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_shareduser"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="shareduser",
                    name="username",
                    field=models.TextField(blank=True, null=True),
                ),
            ],
            database_operations=[],
        ),
    ]
