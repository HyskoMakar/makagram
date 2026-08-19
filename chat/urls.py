from django.urls import path
from . import views

urlpatterns = [
    path('', views.users_list, name='users-list'),
    path('private/<str:username>/', views.private_chat, name='private-chat'),
    path('toggle-friend/<str:username>/', views.toggle_friend, name='toggle-friend'),
    path('toggle-block/<str:username>/', views.toggle_block, name='toggle-block'),
]
