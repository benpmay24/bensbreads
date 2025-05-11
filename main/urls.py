from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('blog/', views.blog, name='blog'),
    path('games/', views.games, name='games'),
    path('about/', views.about, name='about'),
    path('blog/add/', views.add_blog_post, name='add_blog_post'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('blog/delete/<int:post_id>/', views.delete_blog_post, name='delete_blog_post'),
    path('recipes/', views.recipes, name='recipes'),
    path('recipes/add/', views.add_recipe, name='add_recipe'),
    path('recipes/delete/<int:pk>/', views.delete_recipe, name='delete_recipe'),
    path('secrets/', views.secrets, name='secrets'),
    path('ramsey/', views.ramsey_page, name='ramsey'),
    path('ramsey/upload/', views.upload_ramsey_photo, name='upload_ramsey_photo'),
]


# # Serve media files during development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)