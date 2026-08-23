import json
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.me = self.scope['user']
        self.group_id = self.scope['url_route']['kwargs']['group_id']

        if not self.me.is_authenticated:
            await self.close()
            return

        self.room_group_name = f'group_{self.group_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        user_data = await self._get_user_data(self.me)
        # ensure user is member to post
        is_member = await self._is_member(self.me, self.group_id)
        if not is_member:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'You are not a member of this group'}))
            return

        await self._save_message(data.get('message', ''))
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'group.message', 'message': data.get('message', ''), 'user': user_data}
        )

    async def group_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'user': event['user']
        }))

    @sync_to_async
    def _is_member(self, user, group_id):
        from .models import Group
        try:
            g = Group.objects.get(id=group_id)
            return g.members.filter(id=user.id).exists()
        except Exception:
            return False

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
    def _get_last_messages(self):
        from chat.models import GroupMessage
        try:
            msgs = GroupMessage.objects.filter(group_id=self.group_id).select_related('author__profile').order_by('-created_at')[:50]
        except Exception:
            return []
        result = []
        for m in reversed(list(msgs)):
            try:
                avatar = None
                try:
                    if m.author.profile.avatar:
                        avatar = m.author.profile.avatar.url
                except Exception:
                    avatar = None
                user_data = {'username': m.author.profile.username or m.author.username, 'color': m.author.profile.color or 'gray', 'avatar': avatar}
            except Exception:
                user_data = {'username': m.author.username, 'color': 'gray', 'avatar': None}
            result.append({'content': m.content, 'user': user_data})
        return result

    @sync_to_async
    def _save_message(self, content):
        from chat.models import GroupMessage, Group
        from django.contrib.auth.models import User
        try:
            group = Group.objects.get(id=self.group_id)
        except Group.DoesNotExist:
            return
        GroupMessage.objects.create(group=group, author=self.me, content=content)


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

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        user_data = await self._get_user_data(self.me)
        # check if the other user has blocked me
        to_user = await self._get_user_by_username(self.other_username)
        if to_user:
            blocked = await self._is_blocked_by(to_user, self.me)
            if blocked:
                # notify sender that they are blocked
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'You are blocked by this user'}))
                return

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

    async def chat_state(self, event):
        # Forward friend/block state changes to connected clients in the private room
        payload = {
            'type': 'state',
            'friends': event.get('friends', False),
            'blocked': event.get('blocked', False),
            'actor': event.get('actor')
        }
        await self.send(text_data=json.dumps(payload))

    async def chat_invite(self, event):
        payload = {
            'type': 'invite',
            'invite_id': event.get('invite_id'),
            'group_id': event.get('group_id'),
            'group_name': event.get('group_name'),
            'inviter': event.get('inviter')
        }
        await self.send(text_data=json.dumps(payload))

    async def chat_invite_response(self, event):
        # response to invite accept/decline
        payload = {
            'type': 'invite_response',
            'invite_id': event.get('invite_id'),
            'accepted': event.get('accepted'),
            'group_id': event.get('group_id'),
            'group_name': event.get('group_name'),
            'user': event.get('user')
        }
        await self.send(text_data=json.dumps(payload))

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
    def _get_user_by_username(self, username):
        from django.contrib.auth.models import User
        try:
            return User.objects.get(profile__username=username)
        except User.DoesNotExist:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                return None

    @sync_to_async
    def _is_blocked_by(self, blocker, blocked_user):
        from makagram.models import is_blocked
        try:
            return is_blocked(blocker, blocked_user)
        except Exception:
            return False

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
