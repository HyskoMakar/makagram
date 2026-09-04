from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

ALLOWED_COLORS = [
    'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal',
    'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink',
    'rose', 'slate', 'gray', 'zinc', 'neutral', 'stone', 'taupe', 'mauve',
    'mist', 'olive',
]
DEFAULT_COLOR = 'blue'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    username = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=50, default="")
    color = models.CharField(max_length=25, default=DEFAULT_COLOR)

    avatar = models.ImageField(blank=True, default=None)
    avatar_data = models.BinaryField(blank=True, null=True)
    avatar_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.username or self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, username=instance.username)


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
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Leave empty to send a system notification to every user.',
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='sent_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='system')
    link = models.CharField(max_length=255, default='', blank=True)
    is_read = models.BooleanField(default=False)
    read_by = models.ManyToManyField(User, blank=True, related_name='read_broadcast_notifications')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.recipient.username if self.recipient else 'All Users'
        return f'Notification for {target}: {self.title}'

    @property
    def is_broadcast(self):
        return self.recipient_id is None and self.notification_type == 'system'

    def is_read_by(self, user):
        if self.recipient_id:
            return self.is_read
        return self.read_by.filter(pk=user.pk).exists()

    @classmethod
    def visible_to(cls, user):
        return cls.objects.filter(
            Q(recipient=user) | Q(recipient__isnull=True, notification_type='system')
        ).exclude(sender=user)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.recipient_id is None and self.notification_type != 'system':
            raise ValidationError('Only system notifications can be sent to all users.')
