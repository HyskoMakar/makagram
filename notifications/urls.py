from django.urls import path
from . import views

urlpatterns = [
    path('mute/', views.toggle_mute_view, name='toggle-mute'),
    path('', views.notifications_list_view, name='notifications-list'),
    path('mark-read/', views.mark_notifications_read_view, name='notifications-mark-read'),
    path('<int:notif_id>/read/', views.mark_one_notification_read_view, name='notification-read-one'),
]
