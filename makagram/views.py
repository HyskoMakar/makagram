import re

from PIL import Image, UnidentifiedImageError
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm
from .models import ALLOWED_COLORS, DEFAULT_COLOR, Notification, NotificationMute

MAX_AVATAR_SIZE = 5 * 1024 * 1024
MAX_AVATAR_DIMENSION = 2000


def feed(request):
    tab = request.GET.get('tab', 'all')
    feed_items = []

    if tab in ('all', 'channel'):
        from channel.models import ChannelPost, ChannelPostLike
        channel_posts = ChannelPost.objects.select_related('channel', 'author__profile').prefetch_related('likes').order_by('-created_at')[:30]
        liked_post_ids = set()
        if request.user.is_authenticated:
            liked_post_ids = set(ChannelPostLike.objects.filter(creator=request.user).values_list('post_id', flat=True))

        for post in channel_posts:
            feed_items.append({
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
                'liked': post.id in liked_post_ids,
                'post_id': post.id,
                'link': f'/channel/{post.channel.id}/',
            })

    if tab in ('all', 'group'):
        from chat.models import GroupMessage, Group
        if request.user.is_authenticated:
            my_group_ids = Group.objects.filter(members=request.user).values_list('id', flat=True)
            group_msgs = GroupMessage.objects.filter(group_id__in=my_group_ids).select_related('group', 'author__profile').order_by('-created_at')[:30]
        else:
            public_group_ids = Group.objects.filter(private=False).values_list('id', flat=True)
            group_msgs = GroupMessage.objects.filter(group_id__in=public_group_ids).select_related('group', 'author__profile').order_by('-created_at')[:30]

        for msg in group_msgs:
            feed_items.append({
                'id': f'group_{msg.id}',
                'type': 'group',
                'type_label': 'Group',
                'title': msg.group.name,
                'color': msg.group.color or 'purple',
                'content': msg.content,
                'created_at': msg.created_at,
                'author': msg.author,
                'link': f'/chat/groups/{msg.group.id}/',
            })

    if tab in ('all', 'private') and request.user.is_authenticated:
        from chat.models import PrivateMessage
        from django.db.models import Q
        private_msgs = PrivateMessage.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user)
        ).select_related('from_user__profile', 'to_user__profile').order_by('-created_at')[:20]

        for msg in private_msgs:
            other = msg.to_user if msg.from_user == request.user else msg.from_user
            other_username = (other.profile.username if hasattr(other, 'profile') and other.profile.username else other.username) if other else 'User'
            other_color = getattr(getattr(other, 'profile', None), 'color', 'emerald') or 'emerald'
            feed_items.append({
                'id': f'private_{msg.id}',
                'type': 'private',
                'type_label': 'Direct Message',
                'title': f'@{other_username}',
                'color': other_color,
                'content': msg.content,
                'created_at': msg.created_at,
                'author': msg.from_user,
                'link': f'/chat/private/{other.username}/' if other else '#',
            })

    if tab in ('all', 'system'):
        if request.user.is_authenticated:
            sys_notifs = Notification.visible_to(request.user).filter(
                notification_type='system'
            )[:10]
        else:
            sys_notifs = Notification.objects.filter(
                recipient__isnull=True,
                notification_type='system',
            )[:10]

        for n in sys_notifs:
            feed_items.append({
                'id': f'sys_{n.id}',
                'type': 'system',
                'type_label': 'Community',
                'title': n.title,
                'color': 'indigo',
                'content': n.message,
                'created_at': n.created_at,
                'author': n.sender,
                'link': n.link or '/',
            })

    feed_items.sort(key=lambda x: x['created_at'], reverse=True)

    return render(request, 'feed.html', {
        'feed_items': feed_items[:50],
        'tab': tab,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('room-index')

    form = LoginForm(data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('room-index')
    return render(request, 'login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('room-index')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('room-index')
    return render(request, 'register.html', {'form': form})


@login_required(login_url='login')
def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


@login_required(login_url='login')
def profile_view(request):
    profile = request.user.profile

    if profile.color not in ALLOWED_COLORS:
        profile.color = DEFAULT_COLOR
        profile.save(update_fields=['color'])

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()[:50]
        description = request.POST.get('description', '').strip()[:50]
        color = request.POST.get('color', DEFAULT_COLOR)

        if username and re.fullmatch(r'[A-Za-z0-9_-]{1,50}', username):
            profile.username = username
        elif username:
            return render(request, 'profile.html', {
                'profile': profile,
                'colors': ALLOWED_COLORS,
                'error': 'Nickname can contain only letters, numbers, _ and -.',
            })
        profile.description = description
        profile.color = color if color in ALLOWED_COLORS else DEFAULT_COLOR

        if 'clear_avatar' in request.POST:
            profile.avatar_data = None
            profile.avatar_type = ''

            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None

        elif 'avatar' in request.FILES:
            avatar = request.FILES['avatar']

            if avatar.size > 2 * 1024 * 1024:
                return render(request, 'profile.html', {
                    'profile': profile,
                    'colors': ALLOWED_COLORS,
                    'error': 'Avatar must be smaller than 2 MB.'
                })

            profile.avatar_data = avatar.read()
            profile.avatar_type = avatar.content_type

            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None

        profile.save()
        return redirect('profile')

    return render(request, 'profile.html', {
        'profile': profile,
        'colors': ALLOWED_COLORS,
    })

def avatar_view(request, user_id):
    from django.contrib.auth.models import User

    try:
        profile = User.objects.get(id=user_id).profile
    except User.DoesNotExist:
        return HttpResponse(status=404)

    if not profile.avatar_data:
        return HttpResponse(status=404)

    return HttpResponse(
        profile.avatar_data,
        content_type=profile.avatar_type or 'image/jpeg'
    )


def create_notification_if_not_muted(recipient, sender, title, message, notification_type, link, chat_type=None, target_id=None):
    if sender and recipient == sender:
        return None
    if chat_type and target_id:
        if NotificationMute.objects.filter(user=recipient, chat_type=chat_type, target_id=target_id).exists():
            return None
    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )


@login_required(login_url='login')
@require_POST
def toggle_mute_view(request):
    chat_type = request.POST.get('chat_type')
    target_id = request.POST.get('target_id')
    if not chat_type or not target_id:
        return HttpResponseBadRequest('Invalid params')

    mute, created = NotificationMute.objects.get_or_create(
        user=request.user,
        chat_type=chat_type,
        target_id=target_id,
    )
    if not created:
        mute.delete()
        muted = False
    else:
        muted = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({'ok': True, 'muted': muted})

    return redirect(request.META.get('HTTP_REFERER', 'index'))


def _unread_notification_count(user):
    personal = Notification.objects.filter(recipient=user, is_read=False).count()
    broadcast = (
        Notification.objects.filter(recipient__isnull=True, notification_type='system')
        .exclude(read_by=user)
        .count()
    )
    return personal + broadcast


@login_required(login_url='login')
def notifications_list_view(request):
    notifications = Notification.visible_to(request.user).select_related('sender__profile')[:20]
    broadcast_ids = [n.id for n in notifications if n.is_broadcast]
    read_broadcast_ids = set()
    if broadcast_ids:
        read_broadcast_ids = set(
            Notification.read_by.through.objects.filter(
                user=request.user,
                notification_id__in=broadcast_ids,
            ).values_list('notification_id', flat=True)
        )

    data = []
    for n in notifications:
        sender_name = (
            (n.sender.profile.username if hasattr(n.sender, 'profile') and n.sender.profile.username else n.sender.username)
            if n.sender else 'MaKaGram Community'
        )
        is_read = n.is_read if n.recipient_id else n.id in read_broadcast_ids
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'link': n.link,
            'is_read': is_read,
            'sender': sender_name,
            'created_at': n.created_at.strftime('%H:%M %d.%m.%Y'),
        })
    return JsonResponse({
        'ok': True,
        'notifications': data,
        'unread_count': _unread_notification_count(request.user),
    })


@login_required(login_url='login')
@require_POST
def mark_notifications_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    through = Notification.read_by.through
    unread_broadcast_ids = list(
        Notification.objects.filter(recipient__isnull=True, notification_type='system')
        .exclude(read_by=request.user)
        .values_list('id', flat=True)
    )
    if unread_broadcast_ids:
        through.objects.bulk_create(
            [through(notification_id=nid, user_id=request.user.id) for nid in unread_broadcast_ids],
            ignore_conflicts=True,
        )
    return JsonResponse({'ok': True})
