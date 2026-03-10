from django.db import migrations


def seed_price_groups(apps, schema_editor):
    PriceGroup = apps.get_model("warehouse", "PriceGroup")
    for group_name in ("A", "B", "C"):
        PriceGroup.objects.get_or_create(name=group_name)


def unseed_price_groups(apps, schema_editor):
    PriceGroup = apps.get_model("warehouse", "PriceGroup")
    PriceGroup.objects.filter(name__in=["A", "B", "C"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0049_pricegroup_stockproductprice"),
    ]

    operations = [
        migrations.RunPython(seed_price_groups, unseed_price_groups),
    ]
