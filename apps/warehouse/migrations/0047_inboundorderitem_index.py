from django.db import migrations, models


def populate_inbound_item_index(apps, schema_editor):
    InboundOrderItem = apps.get_model("warehouse", "InboundOrderItem")

    order_ids = (
        InboundOrderItem.objects.order_by()
        .values_list("order_id", flat=True)
        .distinct()
    )
    for order_id in order_ids:
        items = InboundOrderItem.objects.filter(order_id=order_id).order_by(
            "created", "id"
        )
        for index, item in enumerate(items):
            InboundOrderItem.objects.filter(pk=item.pk).update(index=index)


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0046_warehousemovement_batch"),
    ]

    operations = [
        migrations.AddField(
            model_name="inboundorderitem",
            name="index",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name="inboundorderitem",
            options={"ordering": ["index", "created"]},
        ),
        migrations.RunPython(populate_inbound_item_index, migrations.RunPython.noop),
    ]
