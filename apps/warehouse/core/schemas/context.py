from django.http.request import HttpRequest
from pydantic import BaseModel


class RequestContext(BaseModel):
    # todo: enforce here? or in the route?
    user_id: int | None = None
    username: str | None = None

    @classmethod
    def from_django_request(cls, req: HttpRequest) -> RequestContext:
        return cls(
            username=req.user.username,
            user_id=req.user.id,
        )
