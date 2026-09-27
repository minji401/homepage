from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_shareduser_guardian_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="login_failures",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="profile",
            name="login_locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="shareduser",
                    name="email",
                    field=models.TextField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="shareduser",
                    name="login_failures",
                    field=models.IntegerField(default=0),
                ),
                migrations.AddField(
                    model_name="shareduser",
                    name="login_locked_until",
                    field=models.TextField(blank=True, null=True),
                ),
            ],
            database_operations=[],
        ),
    ]
