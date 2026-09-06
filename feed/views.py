from django.shortcuts import render


def feed(request):
    tab = request.GET.get('tab', 'all')
    feed_items = []

    if tab in ('all', 'channel'):
        feed_items += _get_channel_items(request)
    if tab in ('all', 'group'):
        feed_items += _get_group_items(request)
    if tab in ('all', 'private') and request.user.is_authenticated:
        feed_items += _get_private_items(request)
    if tab in ('all', 'system'):
        feed_items += _get_system_items(request)

    feed_items.sort(key=lambda x: x['created_at'], reverse=True)
    return render(request, 'feed.html', {'feed_items': feed_items[:50], 'tab': tab})


def _get_channel_items(request):
    from channel.models import Channel, ChannelPost, ChannelPostLike
    if request.user.is_authenticated:
        my_channel_ids = Channel.objects.filter(subscribers=request.user).values_list('id', flat=True)
        posts = ChannelPost.objects.filter(channel_id__in=my_channel_ids).exclude(author=request.user)
    else:
        posts = ChannelPost.objects.all()
    posts = posts.select_related('channel', 'author__profile').prefetch_related('likes').order_by('-created_at')[:30]

    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(ChannelPostLike.objects.filter(creator=request.user).values_list('post_id', flat=True))

    return [{
        'id': f'channel_{post.id}',
        'type': 'channel',
        'type_label': 'Channel',
        'title': post.channel.name,
        'channel_id': post.channel.id,
        'color': post.channel.color or 'blue',
        'content': post.content,
        'created_at': post.created_at,
        'author': post.author,
        'like_count': post.likes.count(),
        'liked': post.id in liked_ids,
        'post_id': post.id,
        'link': f'/channel/{post.channel.id}/',
    } for post in posts]


def _get_group_items(request):
    from chat.models import GroupMessage, Group
    if request.user.is_authenticated:
        my_group_ids = Group.objects.filter(members=request.user).values_list('id', flat=True)
        msgs = GroupMessage.objects.filter(group_id__in=my_group_ids).exclude(author=request.user)
    else:
        public_ids = Group.objects.filter(private=False).values_list('id', flat=True)
        msgs = GroupMessage.objects.filter(group_id__in=public_ids)
    msgs = msgs.select_related('group', 'author__profile').order_by('-created_at')[:30]

    return [{
        'id': f'group_{msg.id}',
        'type': 'group',
        'type_label': 'Group',
        'title': msg.group.name,
        'color': msg.group.color or 'purple',
        'content': msg.content,
        'created_at': msg.created_at,
        'author': msg.author,
        'link': f'/chat/groups/{msg.group.id}/',
    } for msg in msgs]


def _get_private_items(request):
    from chat.models import PrivateMessage
    msgs = PrivateMessage.objects.filter(
        to_user=request.user
    ).select_related('from_user__profile', 'to_user__profile').order_by('-created_at')[:20]

    items = []
    for msg in msgs:
        other = msg.to_user if msg.from_user == request.user else msg.from_user
        other_profile = getattr(other, 'profile', None)
        items.append({
            'id': f'private_{msg.id}',
            'type': 'private',
            'type_label': 'Direct Message',
            'title': f'@{other_profile.display_name if other_profile else other.username}',
            'color': (other_profile.color if other_profile else None) or 'emerald',
            'content': msg.content,
            'created_at': msg.created_at,
            'author': msg.from_user,
            'link': f'/chat/private/{other_profile.display_name if other_profile else other.username}/' if other else '#',
        })
    return items


def _get_system_items(request):
    from notifications.models import Notification
    if request.user.is_authenticated:
        notifs = Notification.visible_to(request.user).filter(notification_type='system')[:10]
    else:
        notifs = Notification.objects.filter(recipient__isnull=True, notification_type='system')[:10]

    return [{
        'id': f'sys_{n.id}',
        'type': 'system',
        'type_label': 'Community',
        'title': n.title,
        'color': 'indigo',
        'content': n.message,
        'created_at': n.created_at,
        'author': n.sender,
        'link': n.link or '/',
    } for n in notifs]
