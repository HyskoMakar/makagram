from django.apps import AppConfig


def _refresh_user(user):
    from .services import maybe_unlock_for_user

    if user is not None:
        maybe_unlock_for_user(user)


def _on_user_saved(sender, instance, **kwargs):
    _refresh_user(instance)


def _on_profile_saved(sender, instance, **kwargs):
    _refresh_user(instance.user)


def _on_friendship_saved(sender, instance, **kwargs):
    _refresh_user(instance.user)
    _refresh_user(instance.friend)


def _on_block_saved(sender, instance, **kwargs):
    _refresh_user(instance.blocker)
    _refresh_user(instance.blocked)


def _on_private_message_saved(sender, instance, **kwargs):
    _refresh_user(instance.from_user)
    _refresh_user(instance.to_user)


def _on_group_message_saved(sender, instance, **kwargs):
    _refresh_user(instance.author)


def _on_group_saved(sender, instance, **kwargs):
    _refresh_user(instance.owner)
    for member in instance.members.all():
        _refresh_user(member)


def _on_group_members_changed(sender, instance, action, pk_set, **kwargs):
    if action not in {'post_add', 'post_remove', 'post_clear'}:
        return
    for user_id in pk_set or ():
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            _refresh_user(user)
    if action in {'post_add', 'post_remove', 'post_clear'}:
        _refresh_user(instance.owner)


def _on_channel_saved(sender, instance, **kwargs):
    _refresh_user(instance.owner)
    for subscriber in instance.subscribers.all():
        _refresh_user(subscriber)
    for admin in instance.admins.all():
        _refresh_user(admin)


def _on_channel_members_changed(sender, instance, action, pk_set, **kwargs):
    if action not in {'post_add', 'post_remove', 'post_clear'}:
        return
    for user_id in pk_set or ():
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            _refresh_user(user)
    _refresh_user(instance.owner)


def _on_channel_post_saved(sender, instance, **kwargs):
    if instance.author:
        _refresh_user(instance.author)


def _on_channel_post_like_saved(sender, instance, **kwargs):
    _refresh_user(instance.creator)


class AchievementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'achievements'

    def ready(self):
        from django.db.models.signals import m2m_changed, post_migrate, post_save

        if getattr(self, '_signals_connected', False):
            return

        post_migrate.connect(self._ensure_default_achievements, sender=self)

        from django.contrib.auth.models import User
        from makagram.models import Profile
        from channel.models import Channel, ChannelPost, ChannelPostLike
        from chat.models import Block, Friendship, Group, GroupMessage, PrivateMessage

        post_save.connect(_on_user_saved, sender=User)
        post_save.connect(_on_profile_saved, sender=Profile)
        post_save.connect(_on_friendship_saved, sender=Friendship)
        post_save.connect(_on_block_saved, sender=Block)
        post_save.connect(_on_private_message_saved, sender=PrivateMessage)
        post_save.connect(_on_group_message_saved, sender=GroupMessage)
        post_save.connect(_on_group_saved, sender=Group)
        m2m_changed.connect(_on_group_members_changed, sender=Group.members.through)
        post_save.connect(_on_channel_saved, sender=Channel)
        m2m_changed.connect(_on_channel_members_changed, sender=Channel.subscribers.through)
        m2m_changed.connect(_on_channel_members_changed, sender=Channel.admins.through)
        post_save.connect(_on_channel_post_saved, sender=ChannelPost)
        post_save.connect(_on_channel_post_like_saved, sender=ChannelPostLike)

        self._signals_connected = True

    def _ensure_default_achievements(self, sender, **kwargs):
        from .services import ensure_default_achievements

        ensure_default_achievements()