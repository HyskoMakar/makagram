from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from achievements.models import Achievement, UserAchievement
from channel.models import ChannelPost
from chat.models import Group, GroupMessage, PrivateMessage
from notifications.models import Notification
from django.contrib.auth.models import User

from django.utils import timezone
from datetime import timedelta
import re

@staff_member_required
@login_required(login_url='login')
def abuse(request):
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

    achievements = Achievement.objects.filter(type='ultra')

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
        return redirect('abuse')

    return render(request, 'abuse.html', {'stats': stats, 'achievements': achievements})


@staff_member_required
def create_achievement(request):
    if request.method != 'POST':
        return render(request, 'abuse_create_achievement.html')

    name = (request.POST.get('name') or '').strip()[:255]
    description = (request.POST.get('description') or '').strip()
    suffix = (request.POST.get('suffix') or '').strip()[:255]
    icon = (request.POST.get('icon') or '').strip()[:10]

    if not name or not description or not suffix or not icon:
        return redirect('abuse')

    Achievement.objects.create(
        key=f'custom_{str(len(Achievement.objects.filter(type='ultra')))}',
        name=name,
        description=description,
        suffix=suffix,
        icon=icon,
        type='ultra',
        hidden=True,
    )
    return redirect('abuse')

@staff_member_required
def edit_achievement(request, key):
    achievement = get_object_or_404(Achievement, key=key)

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()[:255]
        description = (request.POST.get('description') or '').strip()
        suffix = (request.POST.get('suffix') or '').strip()[:255]
        icon = (request.POST.get('icon') or '').strip()[:255]

        achievement.name = name
        achievement.description = description
        achievement.suffix = suffix
        achievement.icon = icon
        achievement.save()

        return redirect('abuse')

    return render(request, 'abuse_edit_achievement.html', {'achievement': achievement})

@staff_member_required
@require_POST
def unlock_achievement(request, key):
    achievement = get_object_or_404(Achievement, key=key)
    user = get_object_or_404(User, username=request.POST.get('username'))

    userachievement = UserAchievement.objects.filter(user=user, achievement=achievement)

    if not userachievement:
        UserAchievement.objects.create(
            user=user,
            achievement=achievement
        )
    else:
        userachievement.delete()

    return redirect('abuse')

@staff_member_required
@require_POST
def delete_achievement(request, key):
    achievement = get_object_or_404(Achievement, key=key)

    achievement.delete()
    return redirect('abuse')