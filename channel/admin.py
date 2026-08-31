from django.contrib import admin
from .models import Channel, ChannelPost, ChannelPostLike


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'color', 'created_at')
    search_fields = ('name', 'owner__username', 'description')
    list_filter = ('color',)


@admin.register(ChannelPost)
class ChannelPostAdmin(admin.ModelAdmin):
    list_display = ('channel', 'author', 'content', 'created_at')
    search_fields = ('channel__name', 'author__username', 'content')


@admin.register(ChannelPostLike)
class ChannelPostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'creator', 'created_at')
    search_fields = ('creator__username',)
