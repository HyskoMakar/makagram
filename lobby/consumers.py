import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

ALLOWED_ROOMS = [f'lobby-{i}' for i in range(1, 11)]
MAX_MESSAGE_LENGTH = 4000
room_users = {}


class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.room_name = self.scope['url_route']['kwargs']['room_name']

        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        if self.room_name not in ALLOWED_ROOMS:
            await self.close(code=4404)
            return

        self.room_group_name = f'chat_{self.room_name}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        room_users.setdefault(self.room_group_name, set()).add(self.channel_name)
        await self.accept()

        for message in await self._get_last_messages():
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message': message['content'],
                'user': message['user'],
            }))

        await self._broadcast_online_count()

    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        users = room_users.get(self.room_group_name)
        if users:
            users.discard(self.channel_name)
            if not users:
                room_users.pop(self.room_group_name, None)
        await self._broadcast_online_count()

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

        await self._save_message(message)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message,
                'user': await self._get_user_data(self.user),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'user': event['user'],
        }))

    async def online_count(self, event):
        await self.send(text_data=json.dumps({
            'type': 'online_count',
            'count': event['count'],
        }))

    async def _send_error(self, message):
        await self.send(text_data=json.dumps({'type': 'error', 'message': message}))

    async def _broadcast_online_count(self):
        count = len(room_users.get(self.room_group_name, set()))
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'online.count', 'count': count},
        )

    @sync_to_async
    def _get_user_data(self, user):
        profile = getattr(user, 'profile', None)
        return {
            'username': (profile.username if profile else '') or user.username,
            'color': (profile.color if profile else '') or 'gray',
        }

    @sync_to_async
    def _save_message(self, content):
        from .models import Message
        Message.objects.create(user=self.user, room=self.room_name, content=content)

    @sync_to_async
    def _get_last_messages(self):
        from .models import Message
        messages = (
            Message.objects.filter(room=self.room_name)
            .select_related('user__profile')
            .order_by('-created_at')[:50]
        )
        result = []
        for message in reversed(list(messages)):
            result.append({
                'content': message.content,
                'user': {
                    'username': (message.user.profile.username or message.user.username),
                    'color': message.user.profile.color or 'gray',
                },
            })
        return result
