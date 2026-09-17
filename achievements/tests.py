from django.contrib.auth import get_user_model
from django.test import TestCase

from chat.models import Group


class AchievementSignalTests(TestCase):
    def test_superuser_achievement_is_granted_on_direct_user_save(self):
        User = get_user_model()
        user = User.objects.create_user(username='direct_admin', password='secret123', is_superuser=False)

        user.is_superuser = True
        user.save()

        self.assertTrue(user.user_achievements.filter(achievement__key='superuser').exists())

    def test_group_membership_change_grants_achievement_automatically(self):
        User = get_user_model()
        user = User.objects.create_user(username='group_member', password='secret123')
        owner = User.objects.create_user(username='group_owner', password='secret123')

        group = Group.objects.create(name='Auto Group', owner=owner, color='green')
        group.members.add(user)

        self.assertTrue(user.user_achievements.filter(achievement__key='first_group').exists())
