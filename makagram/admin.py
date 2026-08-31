from django.contrib import admin
from .models import Profile, Notification, NotificationMute


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'username', 'color')
    search_fields = ('user__username', 'username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('audience', 'sender', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'title', 'message')

    @admin.display(description='Audience')
    def audience(self, obj):
        if obj.recipient_id is None:
            return 'All users'
        return obj.recipient.username


@admin.register(NotificationMute)
class NotificationMuteAdmin(admin.ModelAdmin):
    list_display = ('user', 'chat_type', 'target_id', 'created_at')
    list_filter = ('chat_type',)
    search_fields = ('user__username',)
