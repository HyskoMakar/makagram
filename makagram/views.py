import re
from datetime import timedelta

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from channel.models import ChannelPost
from chat.models import Group, GroupMessage, PrivateMessage
from notifications.models import Notification

from .forms import LoginForm, RegisterForm
from .models import ALLOWED_COLORS, DEFAULT_COLOR

MAX_AVATAR_SIZE = 5 * 1024 * 1024
MAX_AVATAR_DIMENSION = 2000


def index_view(request):
    return render(request, 'index.html')


@login_required(login_url='login')
def admin_abuse_page_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Only admins can send community announcements.')

    stats = {
        'total_users': User.objects.count(),
        'total_private_messages': PrivateMessage.objects.count(),
        'total_group_messages': GroupMessage.objects.count(),
        'total_channel_posts': ChannelPost.objects.count(),
        'total_groups': Group.objects.count(),
        'total_broadcasts': Notification.objects.filter(recipient__isnull=True, notification_type='system').count(),
        'active_last_7_days': User.objects.filter(last_login__gte=timezone.now() - timedelta(days=7)).count(),
        'active_users_today': User.objects.filter(last_login__gte=timezone.now() - timedelta(days=1)).count(),
    }

    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()[:255]
        message = (request.POST.get('message') or '').strip()
        link = ''

        if not title or not message:
            return render(request, 'admin_abuse_page.html', {
                'error': 'Title and message are required.',
                'title': title,
                'message': message,
                'stats': stats,
            })

        match = re.search(r'https?://\S+|/\S+', message)
        if match:
            link = match.group(0)[:255]

        Notification.objects.create(
            recipient=None,
            sender=request.user,
            title=title,
            message=message,
            notification_type='system',
            link=link,
        )
        return redirect('community-broadcast')

    return render(request, 'admin_abuse_page.html', {'stats': stats})


def guide_view(request):
    return render(request, 'guide.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    form = LoginForm(data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('feed')
    return render(request, 'login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('feed')
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
