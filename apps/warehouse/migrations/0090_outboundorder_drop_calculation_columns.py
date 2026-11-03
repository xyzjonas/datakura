from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0089_move_calculations_to_own_tables"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="outboundorder",
            name="calculation_code",
        ),
        migrations.RemoveField(
            model_name="outboundorder",
            name="is_calculation",
        ),
        migrations.AlterField(
            model_name="outboundorder",
            name="state",
            field=models.PositiveIntegerField(
                choices=[
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
                default=2,
            ),
        ),
    ]
