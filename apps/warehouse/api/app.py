from django.core.exceptions import ObjectDoesNotExist
from ninja import NinjaAPI
from ninja.security import django_auth

from apps.warehouse.core.exceptions import ApiBaseException, NotFoundException
from apps.warehouse.core.schemas.base import BaseResponse, ErrorInformation
from .routes.auth import routes as auth_routes
from .routes.warehouse import routes as warehouse_routes
from .routes.product import routes as product_routes
from .routes.customer import routes as customer_routes
from .routes.orders import routes as orders_routes
from .routes.packaging import routes as packaging_routes


api = NinjaAPI(
    auth=django_auth,
    urls_namespace="api/v1",
    version="0.0.1dev1",
    title="DATAKURA",
    description="Datakura system API",
)

api.add_router(router=auth_routes, prefix="auth")
api.add_router(router=warehouse_routes, prefix="warehouse")
api.add_router(router=product_routes, prefix="products")
api.add_router(router=customer_routes, prefix="customers")
api.add_router(router=orders_routes, prefix="orders")
api.add_router(router=packaging_routes, prefix="packaging")


@api.exception_handler(ApiBaseException)
def handle_api_exceptions(request, exc: ApiBaseException):
    return api.create_response(
        request,
        BaseResponse(
            success=False,
            error=ErrorInformation(
                error_code=exc.code.code,
                message=exc.code.default_message,
                exception=str(exc),
            ),
        ).model_dump(),
        status=exc.http_status,
    )


@api.exception_handler(ObjectDoesNotExist)
def handle_not_found_exceptions(request, exc: ObjectDoesNotExist):
    return handle_api_exceptions(request, NotFoundException(str(exc)))
