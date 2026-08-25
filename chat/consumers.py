import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

MAX_MESSAGE_LENGTH = 4000


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.me = self.scope['user']
        self.group_id = self.scope['url_route']['kwargs']['group_id']

        if not self.me.is_authenticated:
            await self.close(code=4401)
            return

        if not await self._is_member(self.me, self.group_id):
            await self.close(code=4403)
            return

        self.room_group_name = f'group_{self.group_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error('Invalid message format')
            return

        message = str(data.get('message', '')).strip()
        if not message:
            return
        if len(message) > MAX_MESSAGE_LENGTH:
            await self._send_error(f'Message is too long (max {MAX_MESSAGE_LENGTH} characters)')
            return

        if not await self._is_member(self.me, self.group_id):
            await self._send_error('You are not a member of this group')
            return

        await self._save_message(message)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'group.message',
                'message': message,
                'user': await self._get_user_data(self.me),
            },
        )

    async def group_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'user': event['user'],
        }))

    async def group_kicked(self, event):
        if event.get('user_id') != self.me.id:
            return
        await self._send_error('You were removed from this group')
        await self.close(code=4403)

    async def group_deleted(self, event):
        await self._send_error('This group was deleted')
        await self.close(code=4404)

    async def _send_error(self, message):
        await self.send(text_data=json.dumps({'type': 'error', 'message': message}))

    @sync_to_async
    def _is_member(self, user, group_id):
        from .models import Group
        return Group.objects.filter(id=group_id, members=user).exists()

    @sync_to_async
    def _get_user_data(self, user):
        profile = getattr(user, 'profile', None)
        avatar = None
        if profile and profile.avatar:
            avatar = profile.avatar.url
        return {
            'username': (profile.username if profile else '') or user.username,
            'color': (profile.color if profile else '') or 'gray',
            'avatar': avatar,
        }

    @sync_to_async
    def _save_message(self, content):
        from .models import Group, GroupMessage
        group = Group.objects.filter(id=self.group_id).first()
        if group:
            GroupMessage.objects.create(group=group, author=self.me, content=content)


class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.me = self.scope['user']
        self.other_username = self.scope['url_route']['kwargs']['username']

        if not self.me.is_authenticated:
            await self.close(code=4401)
            return

        if not await self._get_user_by_username(self.other_username):
            await self.close(code=4404)
            return

        names = sorted([self.me.username, self.other_username])
        self.room_group_name = f'private_{names[0]}_{names[1]}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error('Invalid message format')
            return

        message = str(data.get('message', '')).strip()
        if not message:
            return
        if len(message) > MAX_MESSAGE_LENGTH:
            await self._send_error(f'Message is too long (max {MAX_MESSAGE_LENGTH} characters)')
            return

        to_user = await self._get_user_by_username(self.other_username)
        if not to_user:
            await self._send_error('User not found')
            return

        if await self._is_blocked_by(to_user, self.me) or await self._is_blocked_by(self.me, to_user):
            await self._send_error('Messaging is blocked')
            return

        await self._save_message(to_user, message)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message,
                'user': await self._get_user_data(self.me),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'user': event['user'],
        }))

    async def chat_state(self, event):
        await self.send(text_data=json.dumps({
            'type': 'state',
            'friends': event.get('friends', False),
            'blocked': event.get('blocked', False),
            'actor': event.get('actor'),
        }))

    async def chat_invite(self, event):
        await self.send(text_data=json.dumps({
            'type': 'invite',
            'invite_id': event.get('invite_id'),
            'group_id': event.get('group_id'),
            'group_name': event.get('group_name'),
            'inviter': event.get('inviter'),
        }))

    async def chat_invite_response(self, event):
        await self.send(text_data=json.dumps({
            'type': 'invite_response',
            'invite_id': event.get('invite_id'),
            'accepted': event.get('accepted'),
            'group_id': event.get('group_id'),
            'group_name': event.get('group_name'),
            'user': event.get('user'),
        }))

    async def _send_error(self, message):
        await self.send(text_data=json.dumps({'type': 'error', 'message': message}))

    @sync_to_async
    def _get_user_data(self, user):
        profile = getattr(user, 'profile', None)
        avatar = None
        if profile and profile.avatar:
            avatar = profile.avatar.url
        return {
            'username': (profile.username if profile else '') or user.username,
            'color': (profile.color if profile else '') or 'gray',
            'avatar': avatar,
        }

    @sync_to_async
    def _save_message(self, to_user, content):
        from .models import PrivateMessage
        PrivateMessage.objects.create(
            from_user=self.me,
            to_user=to_user,
            content=content,
        )

    @sync_to_async
    def _get_user_by_username(self, username):
        from django.contrib.auth.models import User
        return (
            User.objects.select_related('profile')
            .filter(profile__username=username)
            .first()
            or User.objects.select_related('profile').filter(username=username).first()
        )

    @sync_to_async
    def _is_blocked_by(self, blocker, blocked_user):
        from .models import Block
        return Block.objects.filter(blocker=blocker, blocked=blocked_user).exists()
