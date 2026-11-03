from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import QuerySet

from apps.warehouse.core.audit_messages import AuditMessages
from apps.warehouse.core.exceptions import WarehouseItemBadRequestError
from apps.warehouse.core.schemas.context import RequestContext
from apps.warehouse.core.schemas.orders import OutboundOrderSchema
from apps.warehouse.core.schemas.shipping import (
    OutboundOrderShippingUpsertSchema,
    ShippingTypeCreateOrUpdateSchema,
)
from apps.warehouse.core.services.audit import audit_service
from apps.warehouse.core.services.outbound_common import with_pricing_details
from apps.warehouse.core.transformation import outbound_order_orm_to_schema
from apps.warehouse.models.audit import AuditAction
from apps.warehouse.models.customer import ContactPerson
from apps.warehouse.models.orders import OutboundOrder
from apps.warehouse.models.shipping import OutboundOrderShipping, ShippingType

_DEFAULT_STATE = "CZ"


def _to_decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


class ShippingService:
    # --- shipping types (CRUD) ---

    @staticmethod
    def get_shipping_types(search_term: str | None = None) -> QuerySet[ShippingType]:
        qs = ShippingType.objects.all()
        if search_term:
            qs = qs.filter(name__icontains=search_term.strip())
        return qs

    @staticmethod
    def create_shipping_type(body: ShippingTypeCreateOrUpdateSchema) -> ShippingType:
        # idempotent: creating "on the fly" twice must not fail
        return ShippingType.objects.get_or_create(name=body.name.strip())[0]

    @staticmethod
    def update_shipping_type(
        type_id: int, body: ShippingTypeCreateOrUpdateSchema
    ) -> ShippingType:
        shipping_type = ShippingType.objects.get(pk=type_id)
        shipping_type.name = body.name.strip()
        shipping_type.save()
        return shipping_type

    @staticmethod
    def delete_shipping_type(type_id: int) -> None:
        shipping_type = ShippingType.objects.get(pk=type_id)
        if shipping_type.shippings.exists():
            raise WarehouseItemBadRequestError(
                f"Shipping type '{shipping_type.name}' is used by existing orders."
            )
        shipping_type.delete()

    # --- order shipping ---

    @staticmethod
    def address_from_contact(contact: ContactPerson | None) -> dict[str, str]:
        """Shipping address fields as seeded from the order's contact person."""
        if contact is None:
            return {}
        return {
            "name": contact.get_full_name(),
            "state": contact.state or contact.customer.state or _DEFAULT_STATE,
            "city": contact.city or "",
            "street": contact.street or "",
            "postal_code": contact.postal_code or "",
            "email": contact.email or "",
            "phone": contact.phone or "",
        }

    @classmethod
    def ensure_order_shipping(cls, order: OutboundOrder) -> OutboundOrderShipping:
        """Get the order's shipping, creating an empty one (address from contact)."""
        return OutboundOrderShipping.objects.get_or_create(
            order=order, defaults=cls.address_from_contact(order.contact)
        )[0]

    @classmethod
    def sync_address_with_contact(cls, order: OutboundOrder) -> None:
        """Rewrite the shipping address from the order's (just changed) contact."""
        if order.contact is None:
            return
        shipping = cls.ensure_order_shipping(order)
        for field, value in cls.address_from_contact(order.contact).items():
            setattr(shipping, field, value)
        shipping.save()

    @staticmethod
    def _schema(order: OutboundOrder) -> OutboundOrderSchema:
        # re-fetch: drop the cached (stale) reverse one-to-one relation
        order = OutboundOrder.objects.get(pk=order.pk)
        return with_pricing_details(outbound_order_orm_to_schema(order), order)

    @classmethod
    def upsert_order_shipping(
        cls,
        order_code: str,
        params: OutboundOrderShippingUpsertSchema,
        context: RequestContext,
    ) -> OutboundOrderSchema:
        order = OutboundOrder.objects.get(code=order_code)
        shipping_type = (
            ShippingType.objects.get(pk=params.shipping_type_id)
            if params.shipping_type_id is not None
            else None
        )
        values = dict(
            shipping_type=shipping_type,
            package_number=params.package_number.strip(),
            width=_to_decimal(params.width),
            height=_to_decimal(params.height),
            depth=_to_decimal(params.depth),
            name=params.name.strip(),
            state=params.state,
            city=params.city.strip(),
            street=params.street.strip(),
            postal_code=params.postal_code.strip(),
            email=params.email.strip(),
            phone=params.phone.strip(),
            price=_to_decimal(params.price),
            price_with_vat=_to_decimal(params.price_with_vat),
        )
        with transaction.atomic():
            shipping = cls.ensure_order_shipping(order)
            for field, value in values.items():
                setattr(shipping, field, value)
            shipping.save()
            audit_service.add_entry(
                order,
                action=AuditAction.UPDATE,
                user=context.user_id,
                reason=AuditMessages.ORDER_SHIPPING_UPDATED.CS,
            )
        return cls._schema(order)


shipping_service = ShippingService()
