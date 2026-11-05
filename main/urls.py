from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.conf import settings
from . import views


class OtherSiteRedirectView(RedirectView):
    """Permanently redirect a path to the same path on the other site."""
    permanent = True
    base_url_setting = None

    def get_redirect_url(self, *args, **kwargs):
        url = getattr(settings, self.base_url_setting) + self.request.path
        if self.request.META.get('QUERY_STRING'):
            url += '?' + self.request.META['QUERY_STRING']
        return url


urlpatterns = [
    path('', views.home, name='home'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('recipes/', views.recipes, name='recipes'),
    path('recipes/add/', views.add_recipe, name='add_recipe'),
    path('recipes/edit/<int:pk>/', views.edit_recipe, name='edit_recipe'),
    path('recipes/delete/<int:pk>/', views.delete_recipe, name='delete_recipe'),
    path('recipes/<int:pk>/toggle_featured/', views.toggle_featured_recipe, name='toggle_featured_recipe'),
    path('recipes/<int:pk>/', views.recipe_detail, name='recipe_detail'),
    path('health/', views.health, name='health_check'),
    path('order/', include('orders.urls')),

    # Moved to the playground site
    re_path(r'^(blog|games|ramsey|secrets)(/.*)?$', OtherSiteRedirectView.as_view(base_url_setting='PLAYGROUND_SITE_URL')),
]
