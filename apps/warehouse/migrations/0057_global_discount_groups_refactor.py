from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def _assign_discount_group_codes_and_defaults(apps, schema_editor):
    PriceGroup = apps.get_model("warehouse", "PriceGroup")

    fixed = {
        "A": Decimal("5.00"),
        "B": Decimal("10.00"),
        "C": Decimal("15.00"),
    }
    used_codes = set(
        PriceGroup.objects.exclude(code__isnull=True)
        .exclude(code="")
        .values_list("code", flat=True)
    )

    for group in PriceGroup.objects.order_by("id"):
        key = (group.name or "").strip().upper()
        desired_code = key if key in fixed else f"LEGACY-{group.id}"
        code = desired_code
        if code in used_codes:
            code = f"LEGACY-{group.id}"

        group.code = code
        group.discount_percent = fixed.get(key, Decimal("0.00"))
        group.is_active = True
        group.save(update_fields=["code", "discount_percent", "is_active"])
        used_codes.add(code)

    for code, percent in fixed.items():
        PriceGroup.objects.get_or_create(
            code=code,
            defaults={
                "name": code,
                "discount_percent": percent,
                "is_active": True,
            },
        )


def _backfill_customer_discount_group(apps, schema_editor):
    Customer = apps.get_model("warehouse", "Customer")
    PriceGroup = apps.get_model("warehouse", "PriceGroup")

    by_code = {
        group.code.upper(): group for group in PriceGroup.objects.all() if group.code
    }
    by_name = {
        group.name.upper(): group for group in PriceGroup.objects.all() if group.name
    }

    for customer in Customer.objects.select_related("customer_group").all():
        if customer.discount_group_id:
            continue

        source_name = (customer.customer_group.name or "").strip().upper()
        target = by_code.get(source_name) or by_name.get(source_name)
        if target:
            customer.discount_group_id = target.id
            customer.save(update_fields=["discount_group"])


def _drop_legacy_group_product_prices(apps, schema_editor):
    StockProductPrice = apps.get_model("warehouse", "StockProductPrice")
    StockProductPrice.objects.filter(customer__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0056_creditnotetocustomer_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricegroup",
            name="code",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="pricegroup",
            name="discount_percent",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="pricegroup",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="discount_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="discount_customers",
                to="warehouse.pricegroup",
            ),
        ),
        migrations.RunPython(
            _assign_discount_group_codes_and_defaults,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            _backfill_customer_discount_group, migrations.RunPython.noop
        ),
        migrations.RunPython(
            _drop_legacy_group_product_prices, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="pricegroup",
            name="code",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.RemoveConstraint(
            model_name="stockproductprice",
            name="warehouse_productprice_target_by_type",
        ),
        migrations.RemoveConstraint(
            model_name="stockproductprice",
            name="warehouse_unique_product_group_discount",
        ),
        migrations.RemoveConstraint(
            model_name="stockproductprice",
            name="warehouse_unique_product_customer_discount",
        ),
        migrations.RemoveField(
            model_name="stockproductprice",
            name="group",
        ),
        migrations.RemoveField(
            model_name="stockproductprice",
            name="price_type",
        ),
        migrations.AlterField(
            model_name="stockproductprice",
            name="customer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="product_prices",
                to="warehouse.customer",
            ),
        ),
        migrations.AlterModelOptions(
            name="stockproductprice",
            options={"ordering": ["product", "customer", "discount_percent"]},
        ),
        migrations.AddConstraint(
            model_name="pricegroup",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("discount_percent__gte", 0), ("discount_percent__lte", 100)
                ),
                name="warehouse_pricegroup_discount_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockproductprice",
            constraint=models.CheckConstraint(
                condition=models.Q(("customer__isnull", False)),
                name="warehouse_productprice_customer_required",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockproductprice",
            constraint=models.UniqueConstraint(
                fields=("product", "customer"),
                name="warehouse_unique_product_customer_discount",
            ),
        ),
    ]
