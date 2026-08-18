from django.db import models
from django.contrib.auth.models import User


class PrivateMessage(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.from_user.username} -> {self.to_user.username}: {self.content[:50]}'
