from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('guide/', views.guide_view, name='guide'),

    path('feed/', include('feed.urls')),

    # auth
    path('login/', views.login_view, name='login'),
    path('login/mfa', views.verify_mfa_login, name='verify_mfa_login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/mfa/', views.setup_mfa_view, name='setup_mfa'),
    path('profile/mfa/qr-code/', views.generate_qr_code, name='generate_qr_code'),
    path('profile/mfa/verify/', views.verify_mfa, name='verify_mfa'),
    path('profile/mfa/remove/', views.remove_mfa, name='remove_mfa'),
    path('avatar/<int:user_id>/', views.avatar_view, name='avatar'),

    # apps
    path('lobby/', include('lobby.urls')),
    path('chat/', include('chat.urls')),
    path('channel/', include('channel.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('admin/abuse/', views.admin_abuse_page_view, name='admin-abuse'),
    path('achievements/', include('achievements.urls')),

    # admin
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
