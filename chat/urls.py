from django.urls import path
from . import views

urlpatterns = [
    path('', views.chats_list, name='chats-list'),

    path('groups/create/', views.create_group, name='group-create'),
    path('groups/<int:group_id>/', views.group, name='group-view'),
    path('groups/<int:group_id>/invite/', views.invite_to_group, name='group-invite'),
    path('groups/<int:group_id>/edit/', views.edit_group, name='group-edit'),
    path('groups/<int:group_id>/delete/', views.delete_group, name='group-delete'),
    path('groups/<int:group_id>/leave/', views.leave_group, name='group-leave'),
    path('groups/<int:group_id>/join/', views.join_group, name='group-join'),
    path('groups/<int:group_id>/kick/<str:username>/', views.kick_member, name='group-kick'),

    path('invites/<int:invite_id>/accept/', views.accept_invite, name='accept-invite'),
    path('invites/<int:invite_id>/decline/', views.decline_invite, name='decline-invite'),

    path('private/<str:username>/', views.private_chat, name='private-chat'),
    
    path('toggle-friend/<str:username>/', views.toggle_friend, name='toggle-friend'),
    path('toggle-block/<str:username>/', views.toggle_block, name='toggle-block'),

    path('api/mute/', views.toggle_mute_view, name='toggle-mute'),
    path('api/notifications/', views.notifications_list_view, name='notifications-list'),
    path('api/notifications/mark-read/', views.mark_notifications_read_view, name='notifications-mark-read'),
]

