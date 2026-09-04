from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from makagram.models import ALLOWED_COLORS

from .models import Channel, ChannelPost, ChannelPostLike


def _room_name(channel_id):
    return f'channel_{channel_id}'


def _send_channel_event(channel_id, event):
    async_to_sync(get_channel_layer().group_send)(_room_name(channel_id), event)


def _author_payload(user):
    profile = getattr(user, 'profile', None)
    avatar = None
    if profile and getattr(profile, 'avatar_data', None):
        avatar = f'/avatar/{user.id}/'
    return {
        'id': user.id,
        'username': (profile.username if profile else '') or user.username,
        'color': (profile.color if profile else '') or 'gray',
        'avatar': avatar,
    }


@login_required(login_url='login')
def channels_list(request):
    tab = request.GET.get('tab', 'all')

    match tab:
        case 'mine':
            channels = Channel.objects.filter(subscribers=request.user)
        case 'owned':
            channels = request.user.owned_channels.all()
        case 'opped':
            channels = request.user.admin_channels.all()
        case _:
            tab = 'all'
            channels = Channel.objects.all()

    channels = channels.distinct().order_by('-created_at')
    my_channel_ids = set(
        Channel.objects.filter(subscribers=request.user).values_list('id', flat=True)
    )

    return render(request, 'channels.html', {
        'channels': [
            {
                'channel': channel,
                'subscriber_count': channel.subscribers.count(),
                'last_post': channel.posts.order_by('-created_at').first(),
            }
            for channel in channels
        ],
        'tab': tab,
        'my_channel_ids': my_channel_ids,
    })


class ChannelForm(forms.Form):
    name = forms.CharField(max_length=100)
    description = forms.CharField(max_length=100, required=False)
    color = forms.CharField(max_length=25, required=False)


@login_required(login_url='login')
def create_channel(request):
    form = ChannelForm()

    if request.method == 'POST':
        form = ChannelForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name'].strip()
            description = form.cleaned_data['description'].strip()
            color = form.cleaned_data['color'] or 'blue'
            color = color if color in ALLOWED_COLORS else 'blue'

            if not name:
                form.add_error('name', 'Channel name cannot be empty.')
            elif Channel.objects.filter(name=name).exists():
                form.add_error('name', 'A channel with this name already exists.')
            else:
                channel = Channel.objects.create(
                    name=name,
                    description=description[:100],
                    color=color,
                    owner=request.user,
                )
                # the creator is automatically a subscriber and an admin
                channel.subscribers.add(request.user)
                channel.admins.add(request.user)
                return redirect('channel-view', channel_id=channel.id)

    return render(request, 'channel_create.html', {
        'form': form,
        'colors': ALLOWED_COLORS,
        'error': None,
    })


@login_required(login_url='login')
def channel(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    is_owner = request.user == channel.owner
    is_admin = is_owner or channel.admins.filter(id=request.user.id).exists()
    is_subscriber = channel.subscribers.filter(id=request.user.id).exists()

    if request.method == 'POST' and is_admin:
        is_fetch = request.headers.get('x-fetch') == '1'

        content = request.POST.get('message', '').strip()
        attachment_ids_raw = request.POST.get('attachment_ids', '')
        attachment_ids = [int(x) for x in attachment_ids_raw.split(',') if x.strip().isdigit()]
        if content or attachment_ids:
            post = ChannelPost.objects.create(
                channel=channel,
                author=request.user,
                content=content[:4000],
            )
            if attachment_ids:
                from chat.models import Attachment
                Attachment.objects.filter(id__in=attachment_ids, uploaded_by=request.user).update(channel_post=post)

            attachments = [att.as_dict() for att in post.attachments.all()]

            _send_channel_event(channel.id, {
                'type': 'channel.post',
                'post': {
                    'id': post.id,
                    'content': post.content,
                    'created_at': post.created_at.strftime('%b %d, %H:%M'),
                    'author': _author_payload(request.user),
                    'attachments': attachments,
                },
            })

            from makagram.views import create_notification_if_not_muted
            notif_msg = content[:100] if content else 'Sent an attachment'
            for sub in channel.subscribers.exclude(id=request.user.id):
                create_notification_if_not_muted(
                    recipient=sub,
                    sender=request.user,
                    title=f'New post in channel "{channel.name}"',
                    message=f'{notif_msg}',
                    notification_type='channel',
                    link=f'/channel/{channel.id}/',
                    chat_type='channel',
                    target_id=channel.id,
                )

            if is_fetch:
                return JsonResponse({'ok': True})
            return redirect('channel-view', channel_id=channel.id)
        elif is_fetch:
            return JsonResponse({'ok': False, 'error': 'Post cannot be empty'})

    posts_qs = ChannelPost.objects.filter(channel=channel).select_related(
        'author__profile'
    ).prefetch_related('likes', 'attachments').order_by('-created_at')[:50]

    posts = list(reversed(posts_qs))

    liked_post_ids = set(
        ChannelPostLike.objects.filter(
            post__channel=channel, creator=request.user
        ).values_list('post_id', flat=True)
    )

    subscribers = []
    admin_ids = set()
    if is_owner:
        subscribers = channel.subscribers.select_related('profile').order_by(
            'profile__username', 'username'
        )
        admin_ids = set(channel.admins.values_list('id', flat=True))

    from makagram.models import NotificationMute
    is_muted = NotificationMute.objects.filter(user=request.user, chat_type='channel', target_id=channel.id).exists()

    return render(request, 'channel.html', {
        'channel': channel,
        'posts': [
            {
                'post': post,
                'like_count': len(post.likes.all()),
                'liked': post.id in liked_post_ids,
            }
            for post in posts
        ],
        'is_admin': is_admin,
        'is_owner': is_owner,
        'is_subscriber': is_subscriber,
        'is_muted': is_muted,
        'subscriber_count': channel.subscribers.count(),
        'subscribers': subscribers,
        'admin_ids': admin_ids,
        'colors': ALLOWED_COLORS,
    })



@login_required(login_url='login')
@require_POST
def edit_channel(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if request.user != channel.owner:
        return HttpResponseBadRequest('Only the channel creator can edit settings')

    name = request.POST.get('name', '').strip()
    color = request.POST.get('color', '').strip()
    description = request.POST.get('description', '').strip()

    if not name:
        messages.error(request, 'Channel name cannot be empty.')
        return redirect('channel-view', channel_id=channel.id)

    if Channel.objects.filter(name=name).exclude(id=channel.id).exists():
        messages.error(request, 'A channel with this name already exists.')
        return redirect('channel-view', channel_id=channel.id)

    channel.name = name
    channel.description = description[:100]
    if color in ALLOWED_COLORS:
        channel.color = color
    channel.save()
    return redirect('channel-view', channel_id=channel.id)


@login_required(login_url='login')
@require_POST
def delete_channel(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if request.user != channel.owner:
        return HttpResponseBadRequest('Only the creator can delete the channel')

    _send_channel_event(channel.id, {'type': 'channel.deleted'})
    from makagram.models import Notification
    Notification.objects.filter(
        notification_type='channel',
        link=f'/channel/{channel.id}/',
    ).delete()
    channel.delete()
    return redirect('channels-list')


@login_required(login_url='login')
@require_POST
def subscribe_channel(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    channel.subscribers.add(request.user)
    return redirect('channel-view', channel_id=channel.id)


@login_required(login_url='login')
@require_POST
def unsubscribe_channel(request, channel_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if request.user == channel.owner:
        return HttpResponseBadRequest('Creator cannot unsubscribe from the channel')

    with transaction.atomic():
        channel.subscribers.remove(request.user)
        # losing subscription always revokes admin rights, even for admins
        channel.admins.remove(request.user)

    from makagram.models import Notification
    Notification.objects.filter(
        recipient=request.user,
        notification_type='channel',
        link=f'/channel/{channel.id}/',
    ).delete()

    _send_channel_event(channel.id, {'type': 'channel.admins_changed'})
    return redirect('channels-list')


@login_required(login_url='login')
@require_POST
def promote_admin(request, channel_id, user_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if request.user != channel.owner:
        return HttpResponseBadRequest('Only the channel creator can manage admins')

    target = get_object_or_404(User, id=user_id)
    if not channel.subscribers.filter(id=target.id).exists():
        return JsonResponse({'ok': False, 'error': 'user is not a subscriber of this channel'})

    channel.admins.add(target)
    _send_channel_event(channel.id, {'type': 'channel.admins_changed'})
    return JsonResponse({'ok': True})


@login_required(login_url='login')
@require_POST
def demote_admin(request, channel_id, user_id):
    channel = get_object_or_404(Channel, id=channel_id)
    if request.user != channel.owner:
        return HttpResponseBadRequest('Only the channel creator can manage admins')

    target = get_object_or_404(User, id=user_id)
    if target == channel.owner:
        return HttpResponseBadRequest('Cannot remove the creator from admins')

    channel.admins.remove(target)
    _send_channel_event(channel.id, {'type': 'channel.admins_changed'})
    return JsonResponse({'ok': True})


@login_required(login_url='login')
@require_POST
def toggle_like(request, channel_id, post_id):
    channel = get_object_or_404(Channel, id=channel_id)
    post = get_object_or_404(ChannelPost, id=post_id, channel=channel)

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('accept', '')
        or request.content_type == 'application/json'
    )

    if not channel.subscribers.filter(id=request.user.id).exists():
        if is_ajax:
            return JsonResponse({'ok': False, 'error': 'only subscribers can like posts'})
        messages.error(request, 'Only subscribers can like posts.')
        return redirect(request.META.get('HTTP_REFERER', 'feed'))

    like = ChannelPostLike.objects.filter(post=post, creator=request.user).first()
    if like:
        like.delete()
        liked = False
    else:
        ChannelPostLike.objects.create(post=post, creator=request.user)
        liked = True

    like_count = post.likes.count()
    _send_channel_event(channel.id, {
        'type': 'channel.like',
        'post_id': post.id,
        'like_count': like_count,
    })

    if is_ajax:
        return JsonResponse({'ok': True, 'liked': liked, 'like_count': like_count})

    return redirect(request.META.get('HTTP_REFERER', 'feed'))


@login_required(login_url='login')
@require_POST
def edit_post(request, channel_id, post_id):
    channel = get_object_or_404(Channel, id=channel_id)
    post = get_object_or_404(ChannelPost, id=post_id, channel=channel)

    is_owner = request.user == channel.owner
    is_admin = is_owner or channel.admins.filter(id=request.user.id).exists()
    if not (is_admin or post.author == request.user):
        return JsonResponse({'ok': False, 'error': 'Permission denied'}, status=403)

    content = request.POST.get('message', '').strip()
    attachment_ids_raw = request.POST.get('attachment_ids', '')
    attachment_ids = [int(x) for x in attachment_ids_raw.split(',') if x.strip().isdigit()] if attachment_ids_raw else None

    if not content and not attachment_ids:
        return JsonResponse({'ok': False, 'error': 'Post content cannot be empty'})
    if len(content) > 4000:
        return JsonResponse({'ok': False, 'error': 'Post is too long'})

    post.content = content
    post.save()

    if attachment_ids is not None:
        from chat.models import Attachment
        post.attachments.exclude(id__in=attachment_ids).delete()
        Attachment.objects.filter(id__in=attachment_ids, uploaded_by=request.user).update(channel_post=post)

    attachments = [att.as_dict() for att in post.attachments.all()]

    _send_channel_event(channel.id, {
        'type': 'channel.post_edited',
        'post_id': post.id,
        'content': post.content,
        'attachments': attachments,
    })

    return JsonResponse({'ok': True, 'content': post.content, 'attachments': attachments})


@login_required(login_url='login')
@require_POST
def delete_post(request, channel_id, post_id):
    channel = get_object_or_404(Channel, id=channel_id)
    post = get_object_or_404(ChannelPost, id=post_id, channel=channel)

    is_owner = request.user == channel.owner
    is_admin = is_owner or channel.admins.filter(id=request.user.id).exists()
    if not (is_admin or post.author == request.user):
        return JsonResponse({'ok': False, 'error': 'Permission denied'}, status=403)

    post_id = post.id
    post.delete()

    _send_channel_event(channel.id, {
        'type': 'channel.post_deleted',
        'post_id': post_id,
    })

    return JsonResponse({'ok': True})