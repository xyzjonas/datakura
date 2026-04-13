from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


def _backfill_fixed_price_from_discount_percent(apps, schema_editor):
    StockProductPrice = apps.get_model("warehouse", "StockProductPrice")

    for item in StockProductPrice.objects.select_related("product").all():
        base_price = Decimal(str(item.product.base_price or 0))
        discount_percent = Decimal(str(item.discount_percent or 0))
        fixed_price = (
            base_price * (Decimal("1") - discount_percent / Decimal("100"))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        item.fixed_price = fixed_price
        item.save(update_fields=["fixed_price"])


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0060_convert_state_strings_to_integers"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockproductprice",
            name="fixed_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.RunPython(
            _backfill_fixed_price_from_discount_percent,
            migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="stockproductprice",
            name="warehouse_productprice_discount_range",
        ),
        migrations.RemoveField(
            model_name="stockproductprice",
            name="discount_percent",
        ),
        migrations.AlterModelOptions(
            name="stockproductprice",
            options={"ordering": ["product", "customer", "fixed_price"]},
        ),
        migrations.AddConstraint(
            model_name="stockproductprice",
            constraint=models.CheckConstraint(
                condition=models.Q(("fixed_price__gte", 0)),
                name="warehouse_productprice_fixed_price_non_negative",
            ),
        ),
    ]
