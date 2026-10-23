from django.conf import settings
from django.db import migrations


def copy_customer_accounts(apps, schema_editor):
    database = schema_editor.connection.alias
    LegacyCustomer = apps.get_model("Customers", "Users")
    auth_app, auth_model = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(auth_app, auth_model)

    for customer in LegacyCustomer.objects.using(database).all():
        username_exists = User.objects.using(database).filter(
            username__iexact=customer.username,
        ).exists()
        email_exists = User.objects.using(database).filter(
            email__iexact=customer.email,
        ).exists()
        if username_exists or email_exists:
            raise RuntimeError(
                "A legacy customer account conflicts with an existing authenticated "
                "user. Resolve the account conflict before applying this migration."
            )
        User.objects.using(database).create(
            username=customer.username,
            email=customer.email,
            password=customer.password,
            is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("Customers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(copy_customer_accounts, migrations.RunPython.noop),
    ]
