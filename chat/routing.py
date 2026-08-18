from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/privatechat/(?P<username>[\w-]+)/$', consumers.PrivateChatConsumer.as_asgi()),
]
