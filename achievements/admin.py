from django.contrib import admin

from .models import Achievement, UserAchievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'key',
        'suffix',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'name',
        'key',
        'suffix',
    )

    ordering = (
        'id',
    )


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'achievement',
        'unlocked_at',
    )

    list_filter = (
        'achievement',
    )

    search_fields = (
        'user__username',
        'achievement__name',
        'achievement__key',
    )

    ordering = (
        '-unlocked_at',
    )