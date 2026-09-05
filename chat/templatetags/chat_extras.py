import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

URL_REGEX = re.compile(
    r'((?:https?://|www\.|\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|dev|app|co|ai|ru|uk|de|fr|me|tv|gg|ly|sh|to|cloud|online|site|store|tech|info|biz|xyz|render\.com)(?:/[^\s<]*)?))([.,\)!?;:]?(?:\s|<|$))',
    re.IGNORECASE
)

MENTION_REGEX = re.compile(r'@([A-Za-z0-9_-]{1,50})')


@register.filter(name='autolink')
def autolink(value):
    if not value:
        return ''
    escaped = escape(value)
    escaped = URL_REGEX.sub(_replace_url, escaped)
    escaped = MENTION_REGEX.sub(_replace_mention, escaped)
    return mark_safe(escaped)


def _replace_url(match):
    url = match.group(1)
    trailing = match.group(2)
    if url.lower().startswith(('http://', 'https://')):
        href = url
    else:
        href = f'https://{url}'
    return f'<a href="{href}" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline hover:text-blue-800 break-all" onclick="event.stopPropagation();">{url}</a>{trailing}'


def _replace_mention(match):
    from django.contrib.auth.models import User
    username = match.group(1)
    exists = User.objects.filter(profile__username=username).exists() or User.objects.filter(username=username).exists()
    if exists:
        return f'<a href="/chat/private/{username}/" class="text-blue-600 font-medium hover:underline" onclick="event.stopPropagation();">@{username}</a>'
    return match.group(0)
