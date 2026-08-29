import re

from PIL import Image, UnidentifiedImageError
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import HttpResponse

from .forms import LoginForm, RegisterForm
from .models import ALLOWED_COLORS, DEFAULT_COLOR

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
        from chat.models import Notification
        sys_notifs = Notification.objects.filter(notification_type='system').order_by('-created_at')[:10]
        if not sys_notifs.exists():
            from django.contrib.auth.models import User
            first_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if first_user:
                Notification.objects.create(
                    recipient=first_user,
                    title='Welcome to MaKaGram!',
                    message='We have launched the main news feed and notification center. You can now keep track of channels and groups in one place, as well as mute notifications for specific chats.',
                    notification_type='system',
                    link='/',
                )
                sys_notifs = Notification.objects.filter(notification_type='system').order_by('-created_at')[:10]

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