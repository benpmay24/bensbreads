from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('blog/', views.blog, name='blog'),
    path('games/', views.games, name='games'),
    path('blog/add/', views.add_blog_post, name='add_blog_post'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('blog/delete/<int:post_id>/', views.delete_blog_post, name='delete_blog_post'),
    path('recipes/', views.recipes, name='recipes'),
    path('recipes/add/', views.add_recipe, name='add_recipe'),
    path('recipes/delete/<int:pk>/', views.delete_recipe, name='delete_recipe'),
    path('recipes/<int:pk>/toggle_featured/', views.toggle_featured_recipe, name='toggle_featured_recipe'),
    path('secrets/', views.secrets, name='secrets'),
    path('ramsey/story/', views.ramsey_bio, name='ramsey'),
    path('ramsey/gallery/', views.ramsey_gallery, name='ramsey_gallery'),
    path('ramsey/upload/', views.upload_ramsey_photo, name='upload_ramsey_photo'),
    path('games/connect4/', views.connect4, name='connect4'),
    path('api/cpu-move/', views.cpu_move, name='cpu_move'),
    path('api/save-result/', views.save_connect4_result, name='save_connect4_result'),
    path('api/leaderboard/', views.connect4_leaderboard, name='connect4_leaderboard'),
]