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
    color = models.CharField(max_length=25, default=DEFAULT_COLOR)
    avatar = models.ImageField(blank=True)

    def __str__(self):
        return self.username or self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, username=instance.username)