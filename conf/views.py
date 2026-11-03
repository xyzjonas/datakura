# views.py
import posixpath

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.views.generic import TemplateView
from django.views.static import serve
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from decouple import config


@method_decorator(ensure_csrf_cookie, name="dispatch")
class VueAppView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sentry_dsn"] = config("VUE_SENTRY_DSN", default="")
        context["sentry_environment"] = config("SENTRY_ENV", default="development")
        return context


PUBLIC_MEDIA_PREFIXES = ("avatars/",)


def serve_media(request: HttpRequest, path: str) -> HttpResponse:
    """
    Serve uploaded media regardless of DEBUG (django's `static()` helper is a no-op
    in production). Avatars are public, everything else (invoices...) needs a login.
    """
    # normalize first, so "avatars/../invoices/x.pdf" can't sneak past the prefix check
    path = posixpath.normpath(path).lstrip("/")
    if not path.startswith(PUBLIC_MEDIA_PREFIXES) and not request.user.is_authenticated:
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)
