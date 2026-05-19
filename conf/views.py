# views.py
from django.views.generic import TemplateView
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
