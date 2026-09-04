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

        action = data.get('action')

        if action == 'edit':
            message_id = data.get('message_id')
            new_content = str(data.get('message', '')).strip()
            attachment_ids = data.get('attachment_ids', [])
            if not message_id or (not new_content and not attachment_ids):
                return
            if len(new_content) > MAX_MESSAGE_LENGTH:
                await self._send_error(f'Message is too long (max {MAX_MESSAGE_LENGTH} characters)')
                return
            if not await self._is_member(self.me, self.group_id):
                await self._send_error('You are not a member of this group')
                return

            ok, attachments = await self._edit_message(message_id, new_content, attachment_ids)
            if ok:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'group.message_edited',
                        'message_id': message_id,
                        'message': new_content,
                        'attachments': attachments,
                    },
                )
            else:
                await self._send_error('Cannot edit this message')
            return

        if action == 'delete':
            message_id = data.get('message_id')
            if not message_id:
                return
            if not await self._is_member(self.me, self.group_id):
                await self._send_error('You are not a member of this group')
                return

            ok = await self._delete_message(message_id)
            if ok:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'group.message_deleted',
                        'message_id': message_id,
                    },
                )
            else:
                await self._send_error('Cannot delete this message')
            return

        message = str(data.get('message', '')).strip()
        attachment_ids = data.get('attachment_ids', [])
        if not message and not attachment_ids:
            return
        if len(message) > MAX_MESSAGE_LENGTH:
            await self._send_error(f'Message is too long (max {MAX_MESSAGE_LENGTH} characters)')
            return

        if not await self._is_member(self.me, self.group_id):
            await self._send_error('You are not a member of this group')
            return

        msg_obj, attachments = await self._save_message(message, attachment_ids)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'group.message',
                'message_id': msg_obj.id if msg_obj else None,
                'message': message,
                'attachments': attachments,
                'user': await self._get_user_data(self.me),
            },
        )

    async def group_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event.get('message_id'),
            'message': event['message'],
            'attachments': event.get('attachments', []),
            'user': event['user'],
        }))

    async def group_message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'edit_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'attachments': event.get('attachments', []),
        }))

    async def group_message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delete_message',
            'message_id': event['message_id'],
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
        if profile and profile.avatar_data:
            avatar = f'/avatar/{user.id}/'
        return {
            'username': (profile.username if profile else '') or user.username,
            'color': (profile.color if profile else '') or 'gray',
            'avatar': avatar,
        }

    @sync_to_async
    def _save_message(self, content, attachment_ids):
        from .models import Attachment, Group, GroupMessage
        from makagram.views import create_notification_if_not_muted
        group = Group.objects.filter(id=self.group_id).first()
        if group:
            msg = GroupMessage.objects.create(group=group, author=self.me, content=content)
            if attachment_ids:
                Attachment.objects.filter(id__in=attachment_ids, uploaded_by=self.me).update(group_message=msg)
            attachments = [att.as_dict() for att in msg.attachments.all()]

            notif_msg = content[:100] if content else 'Sent an attachment'
            for member in group.members.exclude(id=self.me.id):
                create_notification_if_not_muted(
                    recipient=member,
                    sender=self.me,
                    title=f'Message in group "{group.name}"',
                    message=f'{notif_msg}',
                    notification_type='group',
                    link=f'/chat/groups/{group.id}/',
                    chat_type='group',
                    target_id=group.id,
                )
            return msg, attachments
        return None, []

    @sync_to_async
    def _edit_message(self, message_id, new_content, attachment_ids):
        from .models import Attachment, GroupMessage
        msg = GroupMessage.objects.filter(id=message_id, group_id=self.group_id, author=self.me).first()
        if not msg:
            return False, []
        msg.content = new_content
        msg.save()
        if attachment_ids is not None:
            # Delete removed attachments
            msg.attachments.exclude(id__in=attachment_ids).delete()
            # Link new attachments
            Attachment.objects.filter(id__in=attachment_ids, uploaded_by=self.me).update(group_message=msg)
        attachments = [att.as_dict() for att in msg.attachments.all()]
        return True, attachments

    @sync_to_async
    def _delete_message(self, message_id):
        from .models import Group, GroupMessage
        msg = GroupMessage.objects.filter(id=message_id, group_id=self.group_id).first()
        if not msg:
            return False
        group = Group.objects.filter(id=self.group_id).first()
        if msg.author == self.me or (group and group.owner == self.me):
            msg.delete()
            return True
        return False




class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.me = self.scope['user']
        self.other_username = self.scope['url_route']['kwargs']['username']

        if not self.me.is_authenticated:
            await self.close(code=4401)
            return

        other_user = await self._get_user_by_username(self.other_username)
        if not other_user:
            await self.close(code=4404)
            return

        user_ids = sorted([self.me.id, other_user.id])
        self.room_group_name = f'private_{user_ids[0]}_{user_ids[1]}'

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

        action = data.get('action')

        if action == 'edit':
            message_id = data.get('message_id')
            new_content = str(data.get('message', '')).strip()
            attachment_ids = data.get('attachment_ids', [])
            if not message_id or (not new_content and not attachment_ids):
                return
            if len(new_content) > MAX_MESSAGE_LENGTH:
                await self._send_error(f'Message is too long (max {MAX_MESSAGE_LENGTH} characters)')
                return
            ok, attachments = await self._edit_message(message_id, new_content, attachment_ids)
            if ok:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message_edited',
                        'message_id': message_id,
                        'message': new_content,
                        'attachments': attachments,
                    },
                )
            else:
                await self._send_error('Cannot edit this message')
            return

        if action == 'delete':
            message_id = data.get('message_id')
            if not message_id:
                return
            ok = await self._delete_message(message_id)
            if ok:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message_deleted',
                        'message_id': message_id,
                    },
                )
            else:
                await self._send_error('Cannot delete this message')
            return

        message = str(data.get('message', '')).strip()
        attachment_ids = data.get('attachment_ids', [])
        if not message and not attachment_ids:
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

        msg_obj, attachments = await self._save_message(to_user, message, attachment_ids)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message_id': msg_obj.id if msg_obj else None,
                'message': message,
                'attachments': attachments,
                'user': await self._get_user_data(self.me),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event.get('message_id'),
            'message': event['message'],
            'attachments': event.get('attachments', []),
            'user': event['user'],
        }))

    async def chat_message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'edit_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'attachments': event.get('attachments', []),
        }))

    async def chat_message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delete_message',
            'message_id': event['message_id'],
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
        if profile and profile.avatar_data:
            avatar = f'/avatar/{user.id}/'
        return {
            'username': (profile.username if profile else '') or user.username,
            'color': (profile.color if profile else '') or 'gray',
            'avatar': avatar,
        }

    @sync_to_async
    def _save_message(self, to_user, content, attachment_ids):
        from .models import Attachment, PrivateMessage
        from makagram.views import create_notification_if_not_muted
        msg = PrivateMessage.objects.create(
            from_user=self.me,
            to_user=to_user,
            content=content,
        )
        if attachment_ids:
            Attachment.objects.filter(id__in=attachment_ids, uploaded_by=self.me).update(private_message=msg)
        attachments = [att.as_dict() for att in msg.attachments.all()]

        notif_msg = content[:100] if content else 'Sent an attachment'
        sender_name = self.me.profile.username if hasattr(self.me, 'profile') and self.me.profile.username else self.me.username
        create_notification_if_not_muted(
            recipient=to_user,
            sender=self.me,
            title=f'New message from @{sender_name}',
            message=f'{notif_msg}',
            notification_type='private',
            link=f'/chat/private/{sender_name}/',
            chat_type='private',
            target_id=self.me.id,
        )
        return msg, attachments

    @sync_to_async
    def _edit_message(self, message_id, new_content, attachment_ids):
        from .models import Attachment, PrivateMessage
        msg = PrivateMessage.objects.filter(id=message_id, from_user=self.me).first()
        if not msg:
            return False, []
        msg.content = new_content
        msg.save()
        if attachment_ids is not None:
            # Delete removed attachments
            msg.attachments.exclude(id__in=attachment_ids).delete()
            # Link new attachments
            Attachment.objects.filter(id__in=attachment_ids, uploaded_by=self.me).update(private_message=msg)
        attachments = [att.as_dict() for att in msg.attachments.all()]
        return True, attachments

    @sync_to_async
    def _delete_message(self, message_id):
        from .models import PrivateMessage
        msg = PrivateMessage.objects.filter(id=message_id, from_user=self.me).first()
        if not msg:
            return False
        msg.delete()
        return True

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
