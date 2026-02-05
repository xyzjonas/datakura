"""
URL configuration for dayswithoutaccident project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include, re_path

from .views import VueAppView


def assets_redirect(request, path):
    return redirect(f"/static/assets/{path}", permanent=False)


urlpatterns = [
    path("", include("warehouse.urls")),
    path("admin", admin.site.urls),
    # Quasar/Vite looks for .woff2 in `/assets/...` and not `/static/...` (a bit hackish but works)
    path("assets/<path:path>", assets_redirect),
    re_path(r"^.*$", VueAppView.as_view(), name="vue-app"),  # Catch-all for Vue routing
]
