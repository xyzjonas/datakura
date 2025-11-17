from ninja import NinjaAPI
from ninja.security import django_auth

from apps.warehouse.core.exceptions import NotFound
from .routes.auth import routes as auth_routes
from .routes.warehouse import routes as warehouse_routes
from .routes.product import routes as product_routes
from .routes.customer import routes as customer_routes
from .routes.orders import routes as orders_routes


api = NinjaAPI(
    auth=django_auth,
    urls_namespace="api/v1",
    version="0.0.1dev1",
    title="DATAKURA",
    description="Datakura system API",
)

api.add_router(router=auth_routes, prefix="auth")
api.add_router(router=warehouse_routes, prefix="")
api.add_router(router=product_routes, prefix="products")
api.add_router(router=customer_routes, prefix="customers")
api.add_router(router=orders_routes, prefix="orders")


@api.exception_handler(NotFound)
def service_unavailable(request, exc):
    return api.create_response(
        request,
        {"success": False, "message": "Entity not found"},
        status=404,
    )
