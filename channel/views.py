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
        content = request.POST.get('message', '').strip()
        if content:
            post = ChannelPost.objects.create(
                channel=channel,
                author=request.user,
                content=content[:4000],
            )
            _send_channel_event(channel.id, {
                'type': 'channel.post',
                'post': {
                    'id': post.id,
                    'content': post.content,
                    'created_at': post.created_at.strftime('%b %d, %H:%M'),
                    'author': _author_payload(request.user),
                },
            })
            return redirect('channel-view', channel_id=channel.id)

    posts_qs = ChannelPost.objects.filter(channel=channel).select_related(
        'author__profile'
    ).prefetch_related('likes').order_by('-created_at')[:50]
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

    if not channel.subscribers.filter(id=request.user.id).exists():
        return JsonResponse({'ok': False, 'error': 'only subscribers can like posts'})

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
    return JsonResponse({'ok': True, 'liked': liked, 'like_count': like_count})