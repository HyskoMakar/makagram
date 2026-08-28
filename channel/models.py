from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

# Create your models here.
class Channel(models.Model):
    subscribers = models.ManyToManyField(User, related_name='subscribed_channels', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_channels')
    admins = models.ManyToManyField(User, related_name='admin_channels', blank=True)

    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=25, default='blue')
    description = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.name


class ChannelPost(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='channel_posts',
        null=True,
        blank=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.channel.name}: {self.content[:50]}'


class ChannelPostLike(models.Model):
    post = models.ForeignKey(ChannelPost, on_delete=models.CASCADE, related_name='likes')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_post_likes',
    )
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('post', 'creator')

    def __str__(self):
        return f'{self.creator.username} likes post #{self.post_id}'