from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('blog/', views.blog, name='blog'),
    path('games/', views.games, name='games'),
    path('games/connect4/', views.connect4, name='connect4'),
    path('games/word-find/', views.word_find, name='word_find'),
    path('blog/add/', views.add_blog_post, name='add_blog_post'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('blog/delete/<int:post_id>/', views.delete_blog_post, name='delete_blog_post'),
    path('recipes/', views.recipes, name='recipes'),
    path('recipes/add/', views.add_recipe, name='add_recipe'),
    path('recipes/edit/<int:pk>/', views.edit_recipe, name='edit_recipe'),
    path('recipes/delete/<int:pk>/', views.delete_recipe, name='delete_recipe'),
    path('recipes/<int:pk>/toggle_featured/', views.toggle_featured_recipe, name='toggle_featured_recipe'),
    path('secrets/', views.secrets, name='secrets'),
    path('daily-update/', views.daily_update, name='daily_update'),
    path('daily-update/search/', views.search_daily_update, name='search_daily_update'),
    path('ramsey/story/', views.ramsey_bio, name='ramsey'),
    path('ramsey/gallery/', views.ramsey_gallery, name='ramsey_gallery'),
    path('ramsey/upload/', views.upload_ramsey_photo, name='upload_ramsey_photo'),
    path('ramsey/photo/<int:pk>/delete/', views.delete_ramsey_photo, name='delete_ramsey_photo'),
    path('api/cpu-move/', views.cpu_move, name='cpu_move'),
    path('api/save-result/', views.save_connect4_result, name='save_connect4_result'),
    path('api/leaderboard/', views.connect4_leaderboard, name='connect4_leaderboard'),
    path('health/', views.health, name='health_check'),
    path('recipes/<int:pk>/', views.recipe_detail, name='recipe_detail'),
    path('api/validate-word/', views.validate_word, name='validate_word'),
    path('api/word-find-leaderboard/', views.word_find_leaderboard, name='word_find_leaderboard'),
    path('api/save-word-find-result/', views.save_word_find_result, name='save_word_find_result'),

    # Reviews URLs
    path('reviews/', views.reviews, name='reviews'),
    path('reviews/<int:pk>/', views.review_detail, name='review_detail'),
    path('reviews/add/', views.add_review, name='add_review'),
    path('reviews/<int:pk>/edit/', views.edit_review, name='edit_review'),
    path('reviews/<int:pk>/delete/', views.delete_review, name='delete_review'),
    
    # Google Places API proxy
    path('api/place-search/', views.place_search, name='place_search'),
    path('api/place-photo/', views.place_photo, name='place_photo'),
]