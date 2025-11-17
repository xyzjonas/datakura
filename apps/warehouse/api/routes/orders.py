from typing import cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate

from apps.warehouse.api.pagination import IncomingOrdersPagination
from apps.warehouse.core.schemas.orders import IncomingOrderSchema
from apps.warehouse.core.transformation import incoming_order_orm_to_schema
from apps.warehouse.models.orders import IncomingOrder

routes = Router(tags=["incoming_order"])


@routes.get("", response={200: list[IncomingOrderSchema]}, auth=None)
@paginate(IncomingOrdersPagination)
def get_incoming_orders(request: HttpRequest, search_term: str | None = None):
    """
    List incoming orders, optionally filtered by code or supplier name.
    """
    qs = cast(QuerySet[IncomingOrder], IncomingOrder.objects.select_related("supplier"))
    if search_term:
        search_term = search_term.lower()
        qs = qs.filter(
            Q(code__iexact=search_term)
            | Q(code__icontains=search_term)
            | Q(supplier__name__icontains=search_term)
        )

    return qs.all()


@routes.get("/{order_code}", response={200: IncomingOrderSchema}, auth=None)
def get_incoming_order(request: HttpRequest, order_code: str):
    """
    Retrieve a single incoming order by code.
    """
    return incoming_order_orm_to_schema(IncomingOrder.objects.get(code=order_code))


#
# @routes.post("", response={201: IncomingOrderReadSchema}, auth=None)
# def create_incoming_order(request: HttpRequest, payload: IncomingOrderCreateSchema):
#     """
#     Create a new incoming order.
#     """
#     order = IncomingOrder.objects.create(**payload.dict())
#     return IncomingOrderReadSchema.from_orm(order)
