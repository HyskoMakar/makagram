from django.urls import path

from . import views


urlpatterns = [
    path('', views.achievements_list, name='achievements-list'),
    path('equip/<int:achievement_id>/', views.equip_achievement, name='achievement-equip'),
    path('unequip/', views.unequip_achievement, name='achievement-unequip'),
]