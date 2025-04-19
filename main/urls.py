from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('blog/', views.blog, name='blog'),
    path('recipes/', views.recipes, name='recipes'),
    path('games/', views.games, name='games'),
    path('about/', views.about, name='about'),
    path('blog/add/', views.add_blog_post, name='add_blog_post'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('blog/delete/<int:post_id>/', views.delete_blog_post, name='delete_blog_post'),
]