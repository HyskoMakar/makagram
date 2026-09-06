import re

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .models import Notification, NotificationMute


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


def cleanup_user_notifications(user):
    if not user or not user.is_authenticated:
        return
    from channel.models import Channel
    from chat.models import Group

    to_delete_ids = []
    checks = [
        (r'/channel/(\d+)/?', 'channel', lambda cid: Channel.objects.filter(id=cid, subscribers=user).exists()),
        (r'/chat/groups/(\d+)/?', ('group', 'invite'), lambda gid: Group.objects.filter(id=gid, members=user).exists()),
    ]

    for pattern, notif_types, is_valid in checks:
        types = (notif_types,) if isinstance(notif_types, str) else notif_types
        for notif in Notification.objects.filter(recipient=user, notification_type__in=types):
            m = re.search(pattern, notif.link)
            if m and is_valid(int(m.group(1))):
                continue
            to_delete_ids.append(notif.id)

    if to_delete_ids:
        Notification.objects.filter(id__in=to_delete_ids).delete()


def _unread_notification_count(user):
    cleanup_user_notifications(user)
    personal = Notification.objects.filter(recipient=user, is_read=False).exclude(sender=user).count()
    broadcast = (
        Notification.objects.filter(recipient__isnull=True, notification_type='system')
        .exclude(sender=user)
        .exclude(read_by=user)
        .count()
    )
    return personal + broadcast


@login_required(login_url='login')
def notifications_list_view(request):
    cleanup_user_notifications(request.user)
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
            n.sender.profile.display_name if n.sender and hasattr(n.sender, 'profile')
            else (n.sender.username if n.sender else 'MaKaGram Community')
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
def mark_one_notification_read_view(request, notif_id):
    n = Notification.objects.filter(id=notif_id).first()
    if not n:
        return JsonResponse({'ok': False})
    if n.recipient_id:
        if n.recipient_id == request.user.id:
            n.is_read = True
            n.save(update_fields=['is_read'])
    else:
        n.read_by.add(request.user)
    return JsonResponse({'ok': True})


@login_required(login_url='login')
@require_POST
def mark_notifications_read_view(request):
    Notification.objects.filter(recipient=request.user).exclude(notification_type='system').delete()

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
