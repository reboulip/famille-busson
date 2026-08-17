"""famille_busson URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic.base import RedirectView
from django.views.static import serve as static_serve

from famille_busson import settings


def healthz(request):
    return HttpResponse("ok")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz),
    path("annuaire/", include("annuaire.urls")),
    path("publications/", include("publications.urls")),
    path("", RedirectView.as_view(pattern_name="home")),
    # Served by Django in prod too (whitenoise only covers STATIC_URL, not uploads).
    path("media/<path:path>", static_serve, {"document_root": settings.MEDIA_ROOT}),
]
