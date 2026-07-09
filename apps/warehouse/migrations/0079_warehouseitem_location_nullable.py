from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0078_outboundorderitem_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="warehouseitem",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="items",
                to="warehouse.warehouselocation",
                help_text="Location where the physical item is stored in the warehouse",
            ),
        ),
    ]
