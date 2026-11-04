"""URL configuration for the playground subdomain (SITE_ROLE=playground)."""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('playground.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
