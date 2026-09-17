import pyotp
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

ALLOWED_COLORS = [
    'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal',
    'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'fuchsia', 'pink',
    'rose',
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

    equipped_achievement = models.ForeignKey('achievements.Achievement', null=True, blank=True, on_delete=models.SET_NULL, related_name='equipped_profiles')

    mfa_secret = models.CharField(db_index=True, max_length=32, default=pyotp.random_base32)
    mfa_enabled = models.BooleanField(default=False)

    @property
    def display_name(self):
        return self.username or self.user.username

    def __str__(self):
        return self.display_name


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, username=instance.username)


