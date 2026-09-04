import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

URL_REGEX = re.compile(
    r'((?:https?://|www\.)[^\s<]+?)([\.,\)\!\?;\:]?(?:\s|<|$))',
    re.IGNORECASE
)

@register.filter(name='autolink')
def autolink(value):
    if not value:
        return ''
    escaped_value = escape(value)

    def replace_url(match):
        url = match.group(1)
        trailing = match.group(2)
        href = url if url.lower().startswith(('http://', 'https://')) else f'http://{url}'
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline hover:text-blue-800 break-all" onclick="event.stopPropagation();">{url}</a>{trailing}'

    result = URL_REGEX.sub(replace_url, escaped_value)
    return mark_safe(result)
