from django.urls import path
from . import views

urlpatterns = [
    path('', views.channels_list, name='channels-list'),
    path('create/', views.create_channel, name='channel-create'),
    path('<int:channel_id>/', views.channel, name='channel-view'),
    path('<int:channel_id>/edit/', views.edit_channel, name='channel-edit'),
    path('<int:channel_id>/delete/', views.delete_channel, name='channel-delete'),

    path('<int:channel_id>/subscribe/', views.subscribe_channel, name='channel-subscribe'),
    path('<int:channel_id>/unsubscribe/', views.unsubscribe_channel, name='channel-unsubscribe'),

    path('<int:channel_id>/admins/<int:user_id>/promote/', views.promote_admin, name='channel-promote'),
    path('<int:channel_id>/admins/<int:user_id>/demote/', views.demote_admin, name='channel-demote'),

    path('<int:channel_id>/posts/<int:post_id>/like/', views.toggle_like, name='channel-post-like'),
]