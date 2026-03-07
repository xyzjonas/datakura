from ninja import Router

routes = Router(tags=["Analytics"])


@routes.get("/inventory-value", summary="Get analytics")
def get_analytics(request):
    return {"message": "Hello from analytics!"}
