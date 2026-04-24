from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0064_customer_default_payment_method_customer_is_self_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="outboundorder",
            name="state",
            field=models.PositiveIntegerField(
                choices=[
                    (1, "Draft"),
                    (2, "Submitted"),
                    (3, "Picking"),
                    (4, "Packing"),
                    (5, "Shipping"),
                    (6, "Completed"),
                    (7, "Cancelled"),
                    (8, "Sent"),
                    (9, "Invoiced"),
                    (10, "Waiting for payment"),
                    (11, "Completed paid"),
                ],
                default=1,
            ),
        ),
    ]
