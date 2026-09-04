from django.test import TestCase
from django.contrib.auth.models import User
from channel.models import Channel, ChannelPost
from chat.models import Group
from makagram.models import Notification

class NotificationCleanupTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.subscriber = User.objects.create_user(username='subscriber', password='password')
        self.channel = Channel.objects.create(name='Test Channel', owner=self.owner)
        self.channel.subscribers.add(self.owner, self.subscriber)
        self.group = Group.objects.create(name='Test Group', owner=self.owner)
        self.group.members.add(self.owner, self.subscriber)

    def test_unsubscribe_deletes_notifications(self):
        notif = Notification.objects.create(
            recipient=self.subscriber,
            sender=self.owner,
            title='Channel Update',
            message='New post',
            notification_type='channel',
            link=f'/channel/{self.channel.id}/',
        )
        self.client.force_login(self.subscriber)
        response = self.client.post(f'/channel/{self.channel.id}/unsubscribe/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Notification.objects.filter(id=notif.id).exists())

    def test_leave_group_deletes_notifications(self):
        notif = Notification.objects.create(
            recipient=self.subscriber,
            sender=self.owner,
            title='Group Msg',
            message='Hello',
            notification_type='group',
            link=f'/chat/groups/{self.group.id}/',
        )
        self.client.force_login(self.subscriber)
        response = self.client.post(f'/chat/groups/{self.group.id}/leave/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Notification.objects.filter(id=notif.id).exists())


class ChannelPostEditDeleteTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='channel_owner', password='password')
        self.user = User.objects.create_user(username='regular_user', password='password')
        self.channel = Channel.objects.create(name='Test Channel 2', owner=self.owner)
        self.channel.subscribers.add(self.owner, self.user)
        self.post = ChannelPost.objects.create(channel=self.channel, author=self.owner, content='Initial Content')

    def test_edit_post_success(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            f'/channel/{self.channel.id}/posts/{self.post.id}/edit/',
            {'message': 'Updated Content'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'))
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, 'Updated Content')

    def test_edit_post_permission_denied(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f'/channel/{self.channel.id}/posts/{self.post.id}/edit/',
            {'message': 'Hacked Content'}
        )
        self.assertEqual(response.status_code, 403)
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, 'Initial Content')

    def test_delete_post_success(self):
        self.client.force_login(self.owner)
        response = self.client.post(f'/channel/{self.channel.id}/posts/{self.post.id}/delete/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'))
        self.assertFalse(ChannelPost.objects.filter(id=self.post.id).exists())

    def test_delete_post_permission_denied(self):
        self.client.force_login(self.user)
        response = self.client.post(f'/channel/{self.channel.id}/posts/{self.post.id}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ChannelPost.objects.filter(id=self.post.id).exists())

