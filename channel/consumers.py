import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class ChannelConsumer(AsyncWebsocketConsumer):
    """
    Broadcasts live updates (new posts, like counts, channel deletion) to
    everyone currently viewing a channel page.

    Posting and liking still go through the regular HTTP views (so all the
    permission checks for admins/subscribers stay in one place) - this
    consumer is only used to push the resulting updates out to connected
    clients in real time.
    """

    async def connect(self):
        self.me = self.scope['user']
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']

        if not self.me.is_authenticated:
            await self.close(code=4401)
            return

        if not await self._channel_exists(self.channel_id):
            await self.close(code=4404)
            return

        self.room_group_name = f'channel_{self.channel_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        # The socket is read-only from the client's perspective - posting and
        # liking are done via POST requests so permissions are enforced.
        await self._send_error('This channel does not accept messages over the socket')

    async def channel_post(self, event):
        await self.send(text_data=json.dumps({
            'type': 'post',
            'post': event['post'],
        }))

    async def channel_like(self, event):
        await self.send(text_data=json.dumps({
            'type': 'like',
            'post_id': event['post_id'],
            'like_count': event['like_count'],
        }))

    async def channel_admins_changed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'admins_changed',
        }))

    async def channel_deleted(self, event):
        await self._send_error('This channel was deleted')
        await self.close(code=4404)

    async def _send_error(self, message):
        await self.send(text_data=json.dumps({'type': 'error', 'message': message}))

    @sync_to_async
    def _channel_exists(self, channel_id):
        from .models import Channel
        return Channel.objects.filter(id=channel_id).exists()