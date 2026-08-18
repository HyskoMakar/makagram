import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.me = self.scope['user']
        self.other_username = self.scope['url_route']['kwargs']['username']

        if not self.me.is_authenticated:
            await self.close()
            return

        # Create a consistent room name regardless of who initiates
        names = sorted([self.me.username, self.other_username])
        self.room_group_name = f'private_{names[0]}_{names[1]}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        messages = await self._get_last_messages()
        for msg in messages:
            await self.send(text_data=json.dumps({'type': 'message', 'message': msg['content'], 'user': msg['user']}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        user_data = await self._get_user_data(self.me)
        await self._save_message(data['message'])
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'chat.message', 'message': data['message'], 'user': user_data}
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'user': event['user']
        }))

    @sync_to_async
    def _get_user_data(self, user):
        try:
            avatar = None
            try:
                if user.profile.avatar:
                    avatar = user.profile.avatar.url
            except Exception:
                avatar = None
            return {'username': user.profile.username or user.username, 'color': user.profile.color or 'gray', 'avatar': avatar}
        except Exception:
            return {'username': user.username, 'color': 'gray', 'avatar': None}

    @sync_to_async
    def _save_message(self, content):
        from django.contrib.auth.models import User
        from chat.models import PrivateMessage
        try:
            to_user = User.objects.get(profile__username=self.other_username)
        except User.DoesNotExist:
            to_user = User.objects.get(username=self.other_username)
        PrivateMessage.objects.create(from_user=self.me, to_user=to_user, content=content)

    @sync_to_async
    def _get_last_messages(self):
        from django.contrib.auth.models import User
        from chat.models import PrivateMessage
        from django.db.models import Q
        try:
            other = User.objects.get(profile__username=self.other_username)
        except User.DoesNotExist:
            try:
                other = User.objects.get(username=self.other_username)
            except User.DoesNotExist:
                return []

        messages = PrivateMessage.objects.filter(
            Q(from_user=self.me, to_user=other) | Q(from_user=other, to_user=self.me)
        ).select_related('from_user__profile').order_by('-created_at')[:50]

        result = []
        for msg in reversed(list(messages)):
            try:
                avatar = None
                try:
                    if msg.from_user.profile.avatar:
                        avatar = msg.from_user.profile.avatar.url
                except Exception:
                    avatar = None
                user_data = {'username': msg.from_user.profile.username or msg.from_user.username, 'color': msg.from_user.profile.color or 'gray', 'avatar': avatar}
            except Exception:
                user_data = {'username': msg.from_user.username, 'color': 'gray', 'avatar': None}
            result.append({'content': msg.content, 'user': user_data})
        return result
