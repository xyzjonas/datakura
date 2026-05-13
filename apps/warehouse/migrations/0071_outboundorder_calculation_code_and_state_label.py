from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0070_price_at_shipment_outbound_wh_order_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboundorder",
            name="calculation_code",
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="outboundorder",
            name="state",
            field=models.PositiveIntegerField(
                choices=[
                    (1, "Calculation"),
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
