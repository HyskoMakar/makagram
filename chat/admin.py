from django.contrib import admin
from .models import Friendship, Block, PrivateMessage, Group, GroupInvite, GroupMessage


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('user', 'friend', 'created_at')
    search_fields = ('user__username', 'friend__username')


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__username', 'blocked__username')


@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'content', 'created_at')
    search_fields = ('from_user__username', 'to_user__username', 'content')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'private', 'color', 'created_at')
    list_filter = ('private', 'color')
    search_fields = ('name', 'owner__username')


@admin.register(GroupInvite)
class GroupInviteAdmin(admin.ModelAdmin):
    list_display = ('group', 'invitee', 'invited_by', 'created_at')
    search_fields = ('group__name', 'invitee__username', 'invited_by__username')


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ('group', 'author', 'content', 'created_at')
    search_fields = ('group__name', 'author__username', 'content')
