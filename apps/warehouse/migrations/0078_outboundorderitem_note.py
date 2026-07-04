from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0077_inboundorder_customer_outboundorder_supplier_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboundorderitem",
            name="note",
            field=models.TextField(blank=True, null=True),
        ),
    ]
