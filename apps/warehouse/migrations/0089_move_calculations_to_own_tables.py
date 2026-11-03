from django.db import migrations

ORDER_STATE_DRAFT = 1
ORDER_STATE_SUBMITTED = 2
CALCULATION_OPEN = 1
CALCULATION_CLOSED = 2

COPIED_HEADER_FIELDS = (
    "external_code",
    "description",
    "note",
    "supplier_id",
    "customer_id",
    "contact_id",
    "currency",
    "requested_delivery_date",
)
COPIED_ITEM_FIELDS = (
    "stock_product_id",
    "amount",
    "index",
    "unit_price",
    "total_price",
    "desired_package_type_id",
    "desired_batch_id",
    "note",
)


def _mirror(apps, order, *, code, state, linked):
    """Copy the order (header + items) into a new calculation row."""
    OutboundCalculation = apps.get_model("warehouse", "OutboundCalculation")
    OutboundCalculationItem = apps.get_model("warehouse", "OutboundCalculationItem")

    calculation = OutboundCalculation.objects.create(
        code=code,
        state=state,
        order=order if linked else None,
        **{field: getattr(order, field) for field in COPIED_HEADER_FIELDS},
    )
    # auto_now(_add) ignores explicit values on create
    OutboundCalculation.objects.filter(pk=calculation.pk).update(
        created=order.created, changed=order.changed
    )
    OutboundCalculationItem.objects.bulk_create(
        OutboundCalculationItem(
            calculation=calculation,
            **{field: getattr(item, field) for field in COPIED_ITEM_FIELDS},
        )
        for item in order.items.all()
    )
    return calculation


def move_calculations(apps, schema_editor):
    """
    Calculations used to be `OutboundOrder` rows flagged `is_calculation`:

    - still-a-calculation rows move to the new tables (open stays open, a cancelled
      one becomes closed) together with their audit trail, and the order row is dropped
    - orders that were confirmed from a calculation get a closed mirror calculation
      (under the original `calculation_code`) linked to them, so history stays intact
    """
    OutboundOrder = apps.get_model("warehouse", "OutboundOrder")
    AuditLog = apps.get_model("warehouse", "AuditLog")
    ContentType = apps.get_model("contenttypes", "ContentType")

    order_type, _ = ContentType.objects.get_or_create(
        app_label="warehouse", model="outboundorder"
    )
    calculation_type, _ = ContentType.objects.get_or_create(
        app_label="warehouse", model="outboundcalculation"
    )

    for order in OutboundOrder.objects.filter(is_calculation=True).order_by("pk"):
        is_open = order.state in (ORDER_STATE_DRAFT, ORDER_STATE_SUBMITTED)
        calculation = _mirror(
            apps,
            order,
            code=order.calculation_code or order.code,
            state=CALCULATION_OPEN if is_open else CALCULATION_CLOSED,
            linked=False,
        )
        AuditLog.objects.filter(content_type=order_type, object_id=order.pk).update(
            content_type=calculation_type, object_id=calculation.pk
        )
        order.delete()  # its items go with it

    confirmed = OutboundOrder.objects.filter(
        is_calculation=False, calculation_code__isnull=False
    ).exclude(calculation_code="")
    for order in confirmed.order_by("pk"):
        _mirror(
            apps,
            order,
            code=order.calculation_code,
            state=CALCULATION_CLOSED,
            linked=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("warehouse", "0088_outbound_calculations"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(move_calculations, migrations.RunPython.noop),
    ]
