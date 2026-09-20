from django.contrib.auth.models import User
from django.db import models

class Achievement(models.Model):
    key = models.CharField(
        max_length=100,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    suffix = models.CharField(
        max_length=50,
    )

    icon = models.CharField(
        max_length=10,
        default='🏆',
    )

    type = models.CharField(
        max_length=10,
        default='common',
    )

    hidden = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    @property
    def is_super(self):
        return self.type == 'super'

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.name} [{self.suffix}]'

class UserAchievement(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_achievements',
    )

    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='unlocked_by',
    )

    unlocked_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ['unlocked_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'achievement'],
                name='unique_user_achievement',
            )
        ]

    def __str__(self):
        return f'{self.user.username} -> {self.achievement.name}'