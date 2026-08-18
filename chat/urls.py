from django.urls import path
from . import views

urlpatterns = [
    path('', views.users_list, name='users-list'),
    path('private/<str:username>/', views.private_chat, name='private-chat'),
]
