from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from makagram.models import ALLOWED_COLORS

from .models import (
    Friendship,
    Group,
    GroupInvite,
    GroupMessage,
    PrivateMessage,
    add_friend,
    block_user,
    is_blocked,
    is_friend,
    remove_friend,
    unblock_user,
)

MAX_GROUP_NAME_LENGTH = 100


def _private_room_name(user1, user2):
    names = sorted([user1.username, user2.username])
    return f'private_{names[0]}_{names[1]}'


def _get_user(username):
    return (
        User.objects.select_related('profile').filter(profile__username=username).first()
        or User.objects.select_related('profile').filter(username=username).first()
    )


def _send_private_event(user1, user2, event):
    async_to_sync(get_channel_layer().group_send)(_private_room_name(user1, user2), event)


@login_required(login_url='login')
def users_list(request):
    tab = request.GET.get('tab', 'all')
    gtab = request.GET.get('gtab', 'all')

    if tab == 'friends':
        friend_ids = Friendship.objects.filter(user=request.user).values_list('friend_id', flat=True)
        users = User.objects.filter(id__in=friend_ids)
    else:
        users = User.objects.exclude(id=request.user.id)
    users = users.select_related('profile')

    last_private = PrivateMessage.objects.filter(
        Q(from_user=request.user, to_user=OuterRef('pk'))
        | Q(from_user=OuterRef('pk'), to_user=request.user)
    ).order_by('-created_at').values('content')[:1]
    users = users.annotate(last_message=Subquery(last_private))

    my_groups = Group.objects.filter(members=request.user)
    my_group_ids = set(my_groups.values_list('id', flat=True))

    if gtab == 'mine':
        groups = my_groups
    else:
        groups = Group.objects.filter(
            Q(private=False) | Q(members=request.user) | Q(invites__invitee=request.user)
        ).distinct()

    last_group = GroupMessage.objects.filter(
        group=OuterRef('pk')
    ).order_by('-created_at').values('content')[:1]
    groups = groups.select_related('owner').annotate(last_message=Subquery(last_group))

    keys = {f'online_user_{user.id}': user.id for user in users}
    online_map = cache.get_many(keys)
    online_ids = {keys[key] for key in online_map}

    return render(request, 'chats.html', {
        'users': [
            {'user': user, 'last_message': user.last_message}
            for user in users
        ],
        'tab': tab,
        'gtab': gtab,
        'online_ids': online_ids,
        'groups': [
            {'group': group, 'last_message': group.last_message}
            for group in groups.order_by('-created_at')
        ],
        'my_group_ids': my_group_ids,
    })


class GroupForm(forms.Form):
    name = forms.CharField(max_length=MAX_GROUP_NAME_LENGTH)
    private = forms.BooleanField(required=False)
    color = forms.CharField(max_length=25, required=False)


@login_required(login_url='login')
def create_group(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name'].strip()
            color = form.cleaned_data['color'] or 'blue'
            color = color if color in ALLOWED_COLORS else 'blue'

            if not name:
                form.add_error('name', 'Group name cannot be empty.')
            elif Group.objects.filter(name=name).exists():
                form.add_error('name', 'A group with this name already exists.')
            else:
                group = Group.objects.create(
                    name=name,
                    owner=request.user,
                    private=form.cleaned_data['private'],
                    color=color,
                )
                group.members.add(request.user)
                return redirect('group-view', group_id=group.id)
    else:
        form = GroupForm()

    return render(request, 'group_create.html', {
        'form': form,
        'colors': ALLOWED_COLORS,
        'error': None,
    })


@login_required(login_url='login')
def group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_member = group.members.filter(id=request.user.id).exists()
    invite = GroupInvite.objects.filter(group=group, invitee=request.user).first()

    if group.private and not is_member and not invite:
        return redirect('chats-list')

    if request.method == 'POST' and is_member:
        content = request.POST.get('message', '').strip()
        if content:
            GroupMessage.objects.create(
                group=group,
                author=request.user,
                content=content[:4000],
            )
            return redirect('group-view', group_id=group.id)

    messages_qs = GroupMessage.objects.filter(group=group).select_related(
        'author__profile'
    ).order_by('-created_at')[:50]

    return render(request, 'group_chat.html', {
        'group': group,
        'messages': reversed(list(messages_qs)) if is_member or not group.private else [],
        'is_member': is_member,
        'invited': bool(invite),
        'invite': invite,
        'colors': ALLOWED_COLORS,
    })


@login_required(login_url='login')
@require_POST
def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user != group.owner:
        return HttpResponseBadRequest('Only the group creator can edit settings')

    name = request.POST.get('name', '').strip()
    color = request.POST.get('color', '').strip()
    private = request.POST.get('private') == '1'
    members_can_invite = request.POST.get('members_can_invite') == '1'

    if not name:
        messages.error(request, 'Group name cannot be empty.')
        return redirect('group-view', group_id=group.id)

    if Group.objects.filter(name=name).exclude(id=group.id).exists():
        messages.error(request, 'A group with this name already exists.')
        return redirect('group-view', group_id=group.id)

    group.name = name
    group.private = private
    if color in ALLOWED_COLORS:
        group.color = color
    if private:
        group.members_can_invite = members_can_invite
    group.save()
    return redirect('group-view', group_id=group.id)


@login_required(login_url='login')
@require_POST
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user != group.owner:
        return HttpResponseBadRequest('Only the creator can delete the group')

    async_to_sync(get_channel_layer().group_send)(
        f'group_{group.id}',
        {'type': 'group.deleted'},
    )
    group.delete()
    return redirect('chats-list')


@login_required(login_url='login')
@require_POST
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user == group.owner:
        return HttpResponseBadRequest('Creator cannot leave the group')
    group.members.remove(request.user)
    return redirect('chats-list')


@login_required(login_url='login')
@require_POST
def kick_member(request, group_id, username):
    group = get_object_or_404(Group, id=group_id)
    if request.user != group.owner:
        return HttpResponseBadRequest('Only group owner can kick members')
    if not group.private:
        return HttpResponseBadRequest('Kicking is only available in private groups')

    user_to_kick = _get_user(username)
    if not user_to_kick:
        return HttpResponseBadRequest('User not found')
    if user_to_kick == group.owner:
        return HttpResponseBadRequest('Cannot kick group owner')

    if group.members.filter(id=user_to_kick.id).exists():
        group.members.remove(user_to_kick)
        async_to_sync(get_channel_layer().group_send)(
            f'group_{group.id}',
            {'type': 'group.kicked', 'user_id': user_to_kick.id},
        )

    return JsonResponse({'ok': True})


@login_required(login_url='login')
@require_POST
def invite_to_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not group.private:
        return JsonResponse({'ok': False, 'error': 'group is not private'})
    if not group.members.filter(id=request.user.id).exists():
        return JsonResponse({'ok': False, 'error': 'not a member'})

    other = _get_user(request.POST.get('username', '').strip())
    if not other:
        return JsonResponse({'ok': False, 'error': 'user not found'})
    if other == request.user:
        return JsonResponse({'ok': False, 'error': 'cannot invite yourself'})
    if group.members.filter(id=other.id).exists():
        return JsonResponse({'ok': False, 'error': 'user is already a member'})

    if request.user != group.owner and not group.members_can_invite:
        return JsonResponse({'ok': False, 'error': 'only the group owner can invite members'})

    invite, created = GroupInvite.objects.get_or_create(
        group=group,
        invitee=other,
        defaults={'invited_by': request.user},
    )
    if not created:
        return JsonResponse({'ok': False, 'error': 'invite already sent'})

    _send_private_event(request.user, other, {
        'type': 'chat.invite',
        'invite_id': invite.id,
        'group_id': group.id,
        'group_name': group.name,
        'inviter': request.user.username,
    })
    return JsonResponse({'ok': True, 'invite_id': invite.id})


@login_required(login_url='login')
@require_POST
def accept_invite(request, invite_id):
    invite = get_object_or_404(GroupInvite, id=invite_id, invitee=request.user)
    group = invite.group
    inviter = invite.invited_by

    with transaction.atomic():
        group.members.add(request.user)
        invite.delete()

    _send_private_event(inviter, request.user, {
        'type': 'chat.invite_response',
        'invite_id': invite_id,
        'accepted': True,
        'group_id': group.id,
        'group_name': group.name,
        'user': request.user.username,
    })
    return JsonResponse({'ok': True})


@login_required(login_url='login')
@require_POST
def decline_invite(request, invite_id):
    invite = get_object_or_404(GroupInvite, id=invite_id, invitee=request.user)
    group = invite.group
    inviter = invite.invited_by
    invite.delete()

    _send_private_event(inviter, request.user, {
        'type': 'chat.invite_response',
        'invite_id': invite_id,
        'accepted': False,
        'group_id': group.id,
        'group_name': group.name,
        'user': request.user.username,
    })
    return JsonResponse({'ok': True})


@login_required(login_url='login')
def private_chat(request, username):
    other = _get_user(username)
    if not other or other == request.user:
        return redirect('users-list')

    blocked_by_other = is_blocked(other, request.user)
    i_blocked = is_blocked(request.user, other)
    friends = is_friend(request.user, other)
    my_private_groups = Group.objects.filter(members=request.user, private=True)

    messages_qs = PrivateMessage.objects.filter(
        Q(from_user=request.user, to_user=other)
        | Q(from_user=other, to_user=request.user)
    ).select_related('from_user__profile').order_by('-created_at')[:50]

    pending_invites = GroupInvite.objects.filter(
        Q(invited_by=request.user, invitee=other)
        | Q(invited_by=other, invitee=request.user)
    ).select_related('group', 'invited_by', 'invitee')

    return render(request, 'private_chat.html', {
        'other': other,
        'blocked_by_other': blocked_by_other,
        'chat_blocked': blocked_by_other or i_blocked,
        'i_blocked': i_blocked,
        'friends': friends,
        'my_private_groups': my_private_groups,
        'messages': reversed(list(messages_qs)),
        'pending_invites': pending_invites,
    })


@login_required(login_url='login')
@require_POST
def toggle_friend(request, username):
    other = _get_user(username)
    if not other or other == request.user:
        return HttpResponseBadRequest('user not found')

    if is_blocked(other, request.user) or is_blocked(request.user, other):
        return JsonResponse({'ok': False, 'error': 'blocked'})

    if is_friend(request.user, other):
        with transaction.atomic():
            remove_friend(request.user, other)
        are_friends = False
    else:
        with transaction.atomic():
            are_friends = add_friend(request.user, other)
        if not are_friends:
            return JsonResponse({'ok': False, 'error': 'cannot add friend'})

    _send_private_event(request.user, other, {
        'type': 'chat.state',
        'friends': are_friends,
        'blocked': is_blocked(request.user, other),
        'actor': request.user.username,
    })
    return JsonResponse({'ok': True, 'friends': are_friends})


@login_required(login_url='login')
@require_POST
def toggle_block(request, username):
    other = _get_user(username)
    if not other or other == request.user:
        return HttpResponseBadRequest('user not found')

    if is_blocked(request.user, other):
        with transaction.atomic():
            unblock_user(request.user, other)
        blocked = False
    else:
        with transaction.atomic():
            block_user(request.user, other)
        blocked = True

    _send_private_event(request.user, other, {
        'type': 'chat.state',
        'blocked': blocked,
        'friends': is_friend(request.user, other),
        'actor': request.user.username,
    })
    return JsonResponse({'ok': True, 'blocked': blocked})


@login_required(login_url='login')
@require_POST
def join_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if group.private:
        return HttpResponseBadRequest('group is private')
    group.members.add(request.user)
    return redirect('group-view', group_id=group.id)
