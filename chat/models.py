from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class Friendship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships')
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'friend')

    def __str__(self):
        return f'{self.user.username} -> {self.friend.username}'


class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f'{self.blocker.username} blocked {self.blocked.username}'


def add_friend(user, other):
    if user == other:
        return False
    if Block.objects.filter(blocker=user, blocked=other).exists() or Block.objects.filter(blocker=other, blocked=user).exists():
        return False
    Friendship.objects.get_or_create(user=user, friend=other)
    Friendship.objects.get_or_create(user=other, friend=user)
    return True


def remove_friend(user, other):
    Friendship.objects.filter(user=user, friend=other).delete()
    Friendship.objects.filter(user=other, friend=user).delete()


def is_friend(user, other):
    return Friendship.objects.filter(user=user, friend=other).exists()


def block_user(blocker, blocked):
    if blocker == blocked:
        return False
    remove_friend(blocker, blocked)
    Block.objects.get_or_create(blocker=blocker, blocked=blocked)
    return True


def unblock_user(blocker, blocked):
    Block.objects.filter(blocker=blocker, blocked=blocked).delete()


def is_blocked(blocker, blocked):
    return Block.objects.filter(blocker=blocker, blocked=blocked).exists()

class PrivateMessage(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.from_user.username} -> {self.to_user.username}: {self.content[:50]}'


class Group(models.Model):
    members = models.ManyToManyField(User, related_name='joined_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_groups')
    
    private = models.BooleanField(default=False)
    members_can_invite = models.BooleanField(default=False)

    color = models.CharField(max_length=25, default='blue')
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class GroupInvite(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invites')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_invites')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_group_invites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'invitee')

    def __str__(self):
        return f'Invite {self.invitee.username} -> {self.group.name} by {self.invited_by.username}'

class GroupMessage(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author.username} in {self.group.name}: {self.content[:50]}'


class NotificationMute(models.Model):
    CHAT_TYPES = (
        ('private', 'Private Chat'),
        ('group', 'Group Chat'),
        ('channel', 'Channel'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_mutes')
    chat_type = models.CharField(max_length=20, choices=CHAT_TYPES)
    target_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'chat_type', 'target_id')

    def __str__(self):
        return f'{self.user.username} muted {self.chat_type}:{self.target_id}'


class Notification(models.Model):
    TYPE_CHOICES = (
        ('system', 'System News'),
        ('channel', 'Channel Post'),
        ('group', 'Group Message'),
        ('private', 'Private Message'),
        ('invite', 'Group Invite'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='system')
    link = models.CharField(max_length=255, default='', blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Notification for {self.recipient.username}: {self.title}'