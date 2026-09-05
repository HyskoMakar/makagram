from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path('', views.feed, name='feed'),

    # auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # profile
    path('profile/', views.profile_view, name='profile'),
    path('avatar/<int:user_id>/', views.avatar_view, name='avatar'),

    # another apps
    path('lobby/', include('lobby.urls')),
    path('chat/', include('chat.urls')),
    path('channel/', include('channel.urls')),

    # notifications
    path('api/mute/', views.toggle_mute_view, name='toggle-mute'),
    path('api/notifications/', views.notifications_list_view, name='notifications-list'),
    path('api/notifications/mark-read/', views.mark_notifications_read_view, name='notifications-mark-read'),
    path('api/notifications/<int:notif_id>/read/', views.mark_one_notification_read_view, name='notification-read-one'),

    # admin
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
