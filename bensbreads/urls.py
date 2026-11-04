"""URL configuration for the main Ben's Breads site (SITE_ROLE=main)."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main import views as main_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    # Override the stock auth views so they can redirect back to the playground.
    path('accounts/login/', main_views.LoginView.as_view()),
    path('accounts/logout/', main_views.LogoutView.as_view()),
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
