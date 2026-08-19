from django.db import models
from django.contrib.auth.models import User
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
    avatar = models.ImageField(blank=True)

    def __str__(self):
        return self.username or self.user.username


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
    # cannot friend if either blocked exists
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
    # remove friendship if exists
    remove_friend(blocker, blocked)
    Block.objects.get_or_create(blocker=blocker, blocked=blocked)
    return True


def unblock_user(blocker, blocked):
    Block.objects.filter(blocker=blocker, blocked=blocked).delete()


def is_blocked(blocker, blocked):
    return Block.objects.filter(blocker=blocker, blocked=blocked).exists()



@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, username=instance.username)