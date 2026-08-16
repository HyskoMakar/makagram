import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

room_users = {}


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        if self.room_group_name not in room_users:
            room_users[self.room_group_name] = set()
        room_users[self.room_group_name].add(self.channel_name)

        await self.accept()

        messages = await self._get_last_messages()
        for msg in messages:
            await self.send(text_data=json.dumps({
                "type": "message",
                "message": msg["content"],
                "username": msg["username"]
            }))

        await self._broadcast_online_count()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if self.room_group_name in room_users:
            room_users[self.room_group_name].discard(self.channel_name)

        await self._broadcast_online_count()

    async def receive(self, text_data):
        data = json.loads(text_data)
        user = self.scope["user"]
        username = await self._get_username(user)

        if user.is_authenticated:
            await self._save_message(user, data["message"])

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat.message", "message": data["message"], "username": username}
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "message",
            "message": event["message"],
            "username": event["username"]
        }))

    async def online_count(self, event):
        await self.send(text_data=json.dumps({"type": "online_count", "count": event["count"]}))

    async def _broadcast_online_count(self):
        count = len(room_users.get(self.room_group_name, set()))
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "online.count", "count": count}
        )

    @sync_to_async
    def _get_username(self, user):
        if not user.is_authenticated:
            return "Анонім"
        try:
            return user.profile.username or user.username
        except Exception:
            return user.username

    @sync_to_async
    def _save_message(self, user, content):
        from room.models import Message
        Message.objects.create(user=user, room=self.room_name, content=content)

    @sync_to_async
    def _get_last_messages(self):
        from room.models import Message
        messages = Message.objects.filter(room=self.room_name).select_related('user__profile').order_by('-created_at')[:50]
        result = []
        for msg in reversed(list(messages)):
            try:
                username = msg.user.profile.username or msg.user.username
            except Exception:
                username = msg.user.username
            result.append({"content": msg.content, "username": username})
        return result
