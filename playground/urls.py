from django.urls import path, re_path
from main.urls import OtherSiteRedirectView
from main.views import health, LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='playground_home'),
    path('blog/', views.blog, name='blog'),
    path('games/', views.games, name='games'),
    path('games/connect4/', views.connect4, name='connect4'),
    path('games/word-find/', views.word_find, name='word_find'),
    path('games/starhold/', views.starhold, name='starhold'),
    path('games/starhold/play/', views.starhold_play, name='starhold_play'),
    path('games/starhold/api/save-result/', views.save_starhold_result, name='save_starhold_result'),
    path('games/starhold/api/leaderboard/', views.starhold_leaderboard, name='starhold_leaderboard'),
    path('blog/add/', views.add_blog_post, name='add_blog_post'),
    path('blog/delete/<int:post_id>/', views.delete_blog_post, name='delete_blog_post'),
    path('secrets/', views.secrets, name='secrets'),
    path('ramsey/story/', views.ramsey_bio, name='ramsey'),
    path('ramsey/gallery/', views.ramsey_gallery, name='ramsey_gallery'),
    path('ramsey/upload/', views.upload_ramsey_photo, name='upload_ramsey_photo'),
    path('ramsey/photo/<int:pk>/delete/', views.delete_ramsey_photo, name='delete_ramsey_photo'),
    path('ramsey/profile/', views.ramsey_profile, name='ramsey_profile'),
    path('ramsey/profile/edit/', views.edit_ramsey_profile, name='edit_ramsey_profile'),
    path('ramsey/vaccines/add/', views.add_vaccine_record, name='add_vaccine_record'),
    path('ramsey/vaccines/<int:pk>/edit/', views.edit_vaccine_record, name='edit_vaccine_record'),
    path('ramsey/vaccines/<int:pk>/delete/', views.delete_vaccine_record, name='delete_vaccine_record'),
    path('ramsey/boarding/add/', views.add_boarding_experience, name='add_boarding_experience'),
    path('ramsey/boarding/<int:pk>/edit/', views.edit_boarding_experience, name='edit_boarding_experience'),
    path('ramsey/boarding/<int:pk>/delete/', views.delete_boarding_experience, name='delete_boarding_experience'),
    path('ramsey/diet/add/', views.add_diet_entry, name='add_diet_entry'),
    path('ramsey/diet/<int:pk>/edit/', views.edit_diet_entry, name='edit_diet_entry'),
    path('ramsey/diet/<int:pk>/delete/', views.delete_diet_entry, name='delete_diet_entry'),
    path('ramsey/vaccines/documents/upload/', views.upload_vaccine_document, name='upload_vaccine_document'),
    path('ramsey/vaccines/documents/<int:pk>/delete/', views.delete_vaccine_document, name='delete_vaccine_document'),
    path('ramsey/diet/documents/upload/', views.upload_diet_document, name='upload_diet_document'),
    path('ramsey/diet/documents/<int:pk>/delete/', views.delete_diet_document, name='delete_diet_document'),
    path('ramsey/boarding/documents/upload/', views.upload_boarding_document, name='upload_boarding_document'),
    path('ramsey/boarding/documents/<int:pk>/delete/', views.delete_boarding_document, name='delete_boarding_document'),
    path('ramsey/documents/download/<str:doc_type>/<int:doc_id>/', views.download_document, name='download_document'),
    path('api/cpu-move/', views.cpu_move, name='cpu_move'),
    path('api/save-result/', views.save_connect4_result, name='save_connect4_result'),
    path('api/leaderboard/', views.connect4_leaderboard, name='connect4_leaderboard'),
    path('api/validate-word/', views.validate_word, name='validate_word'),
    path('api/word-find-leaderboard/', views.word_find_leaderboard, name='word_find_leaderboard'),
    path('api/save-word-find-result/', views.save_word_find_result, name='save_word_find_result'),
    path('health/', health, name='health_check'),
    # Logging out here clears the shared session, so it logs you out of both sites.
    path('logout/', LogoutView.as_view(next_page='playground_home'), name='logout'),

    # Lives on the main site
    re_path(r'^(recipes|order|login|signup|manage-users|accounts)(/.*)?$', OtherSiteRedirectView.as_view(base_url_setting='MAIN_SITE_URL')),
]
