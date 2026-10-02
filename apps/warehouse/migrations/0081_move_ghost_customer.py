from django.db import migrations

GHOST_CODE = "ghost-customer"
GHOST_ID = 2**31 - 1


def move_ghost_customer(apps, schema_editor):
    """Ghost customer got the lowest id; move it to the highest possible one"""
    Customer = apps.get_model("warehouse", "Customer")
    AuditLog = apps.get_model("warehouse", "AuditLog")
    ContentType = apps.get_model("contenttypes", "ContentType")

    ghost = Customer.objects.filter(code=GHOST_CODE).first()
    if ghost is None or ghost.pk == GHOST_ID:
        return
    if Customer.objects.filter(pk=GHOST_ID).exists():
        raise RuntimeError(f"Customer id {GHOST_ID} is taken, cannot move ghost")

    old_id = ghost.pk
    # FK checks are deferred until the end of the migration
    Customer.objects.filter(pk=old_id).update(id=GHOST_ID)
    for relation in Customer._meta.related_objects:
        if relation.one_to_many or relation.one_to_one:
            relation.related_model.objects.filter(
                **{relation.field.name: old_id}
            ).update(**{relation.field.name: GHOST_ID})

    content_type = ContentType.objects.filter(
        app_label="warehouse", model="customer"
    ).first()
    if content_type:
        AuditLog.objects.filter(content_type=content_type, object_id=old_id).update(
            object_id=GHOST_ID
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "warehouse",
            "0080_inboundorderitem_unique_inbound_order_item_order_index_and_more",
        ),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(move_ghost_customer, migrations.RunPython.noop),
    ]
