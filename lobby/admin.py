from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'content', 'created_at')
    list_filter = ('room',)
    search_fields = ('user__username', 'room', 'content')
