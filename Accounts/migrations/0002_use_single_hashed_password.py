from django.contrib.auth.hashers import make_password
from django.db import migrations, models


def hash_existing_passwords(apps, schema_editor):
    Users = apps.get_model("Accounts", "Users")
    for user in Users.objects.using(schema_editor.connection.alias).all().iterator():
        user.password = make_password(user.password)
        user.save(update_fields=["password"])


class Migration(migrations.Migration):

    dependencies = [
        ("Accounts", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="users",
            old_name="password_1",
            new_name="password",
        ),
        migrations.RunPython(hash_existing_passwords, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="users",
            name="password",
            field=models.CharField(max_length=128),
        ),
        migrations.RemoveField(
            model_name="users",
            name="password_2",
        ),
    ]
