from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.warehouse.models.orders import OutboundOrder


@receiver(post_save, sender=OutboundOrder, dispatch_uid="warehouse.order_shipping")
def create_order_shipping(sender, instance: OutboundOrder, created: bool, **kwargs):
    """Every sales order has (possibly empty) shipping information."""
    if created and not kwargs.get("raw"):
        from apps.warehouse.core.services.shipping import shipping_service

        shipping_service.ensure_order_shipping(instance)
