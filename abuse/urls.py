from django.urls import path

from . import views


urlpatterns = [
    path('', views.abuse, name='abuse'),
    path('achievements/create', views.create_achievement, name='abuse-achievement-create'),
    path('achievements/edit/<str:key>', views.edit_achievement, name='abuse-achievement-edit'),
    path('achievements/delete/<str:key>', views.delete_achievement, name='abuse-achievement-delete'),
    path('achievements/unlock/<str:key>', views.unlock_achievement, name='abuse-achievement-unlock')
]