from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.core.cache import cache
from .models import Friendship, is_friend, add_friend, remove_friend, is_blocked, block_user, unblock_user
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from .models import Group, GroupMessage, GroupInvite
from django import forms
from django.shortcuts import get_object_or_404
from django.contrib import messages


@login_required(login_url='login')
def users_list(request):
    tab = request.GET.get('tab', 'all')
    gtab = request.GET.get('gtab', 'all')
    if tab == 'friends':
        friend_ids = Friendship.objects.filter(user=request.user).values_list('friend_id', flat=True)
        users = User.objects.filter(id__in=friend_ids).select_related('profile')
    else:
        users = User.objects.exclude(id=request.user.id).select_related('profile')
    # Groups the current user is a member of
    my_groups_qs = Group.objects.filter(members=request.user)
    my_group_ids = set(my_groups_qs.values_list('id', flat=True))
    if gtab == 'mine':
        groups_qs = my_groups_qs.order_by('-created_at').select_related('owner')
    else:
        # include visible groups: public, member, or invited
        public = Group.objects.filter(private=False)
        invited_groups = Group.objects.filter(invites__invitee=request.user)
        groups_qs = (public | my_groups_qs | invited_groups).distinct().select_related('owner')
    # prepare last message for users
    from django.db.models import Q
    user_entries = []
    for u in users:
        last = None
        try:
            from chat.models import PrivateMessage
            other = u
            pm = PrivateMessage.objects.filter(Q(from_user=request.user, to_user=other) | Q(from_user=other, to_user=request.user)).order_by('-created_at').first()
            if pm:
                last = pm.content
        except Exception:
            last = None
        user_entries.append({'user': u, 'last_message': last})
    # prepare last message for groups
    group_entries = []
    for g in groups_qs:
        last = None
        gm = GroupMessage.objects.filter(group=g).order_by('-created_at').first()
        if gm:
            last = gm.content
        group_entries.append({'group': g, 'last_message': last})
    keys = {f'online_user_{u.id}': u.id for u in users}
    online_map = cache.get_many(list(keys.keys()))
    online_ids = {keys[k] for k in online_map.keys()}
    return render(request, 'chats.html', {
        'users': user_entries,
        'tab': tab,
        'gtab': gtab,
        'online_ids': online_ids,
        'groups': group_entries,
        'my_group_ids': my_group_ids,
    })


class GroupForm(forms.Form):
    name = forms.CharField(max_length=100)
    private = forms.BooleanField(required=False)
    color = forms.CharField(max_length=25, required=False)


@login_required(login_url='login')
def create_group(request):
    from makagram.models import ALLOWED_COLORS
    error = None
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name'].strip()
            color = form.cleaned_data['color'] or 'blue'
            if color not in ALLOWED_COLORS:
                color = 'blue'
            if Group.objects.filter(name=name).exists():
                error = 'A group with this name already exists.'
            else:
                g = Group.objects.create(
                    name=name,
                    owner=request.user,
                    private=form.cleaned_data['private'],
                    color=color
                )
                g.members.add(request.user)
                return redirect('group-view', group_id=g.id)
    else:
        form = GroupForm()
    return render(request, 'group_create.html', {'form': form, 'colors': ALLOWED_COLORS, 'error': error})


@login_required(login_url='login')
def group_view(request, group_id):
    from makagram.models import ALLOWED_COLORS
    group = get_object_or_404(Group, id=group_id)
    is_member = group.members.filter(id=request.user.id).exists()
    invited = GroupInvite.objects.filter(group=group, invitee=request.user).first()
    messages_qs = GroupMessage.objects.filter(group=group).select_related('author__profile').order_by('-created_at')[:50]
    if request.method == 'POST' and is_member:
        content = request.POST.get('message')
        if content:
            GroupMessage.objects.create(group=group, author=request.user, content=content)
            return redirect('group-view', group_id=group.id)
    return render(request, 'group.html', {
        'group': group,
        'messages': reversed(list(messages_qs)),
        'is_member': is_member,
        'invited': bool(invited),
        'invite': invited,
        'colors': ALLOWED_COLORS,
    })


@login_required(login_url='login')
@require_POST
def edit_group(request, group_id):
    from makagram.models import ALLOWED_COLORS
    group = get_object_or_404(Group, id=group_id)
    if request.user != group.owner:
        return HttpResponseBadRequest('Only the group creator can edit settings')

    new_name = request.POST.get('name', '').strip()
    new_color = request.POST.get('color', '').strip()
    is_private = request.POST.get('private') == 'true' or request.POST.get('private') == 'on' or request.POST.get('private') == '1'

    if new_name and new_name != group.name:
        if Group.objects.filter(name=new_name).exclude(id=group.id).exists():
            messages.error(request, 'A group with this name already exists.')
            return redirect('group-view', group_id=group.id)
        group.name = new_name

    if new_color and new_color in ALLOWED_COLORS:
        group.color = new_color

    group.private = is_private
    group.save()
    return redirect('group-view', group_id=group.id)


@login_required(login_url='login')
@require_POST
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user != group.owner:
        return HttpResponseBadRequest('Only the creator can delete the group')
    group.delete()
    return redirect('chats-list')


@login_required(login_url='login')
@require_POST
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.user == group.owner:
        return HttpResponseBadRequest('Creator cannot leave the group')
    if group.members.filter(id=request.user.id).exists():
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
    try:
        user_to_kick = User.objects.get(profile__username=username)
    except User.DoesNotExist:
        try:
            user_to_kick = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponseBadRequest('User not found')

    if user_to_kick == group.owner:
        return HttpResponseBadRequest('Cannot kick group owner')

    if group.members.filter(id=user_to_kick.id).exists():
        group.members.remove(user_to_kick)

    return JsonResponse({'ok': True})


@login_required(login_url='login')
def invite_to_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not group.members.filter(id=request.user.id).exists():
        return HttpResponseBadRequest('not a member')
    username = request.POST.get('username')
    try:
        other = User.objects.get(profile__username=username)
    except User.DoesNotExist:
        try:
            other = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponseBadRequest('user not found')
    if other == request.user:
        return JsonResponse({'ok': False, 'error': 'cannot invite yourself'})
    if group.members.filter(id=other.id).exists():
        return JsonResponse({'ok': False, 'error': 'user is already a member'})
    if not group.private:
        return JsonResponse({'ok': False, 'error': 'group is not private'})
    inv, created = GroupInvite.objects.get_or_create(
        group=group, invitee=other, defaults={'invited_by': request.user}
    )
    if not created:
        return JsonResponse({'ok': False, 'error': 'invite already sent'})
    layer = get_channel_layer()
    names = sorted([request.user.username, other.username])
    room = f'private_{names[0]}_{names[1]}'
    async_to_sync(layer.group_send)(room, {'type': 'chat.invite', 'invite_id': inv.id, 'group_id': group.id, 'group_name': group.name, 'inviter': request.user.username})
    return JsonResponse({'ok': True, 'invite_id': inv.id})


@login_required(login_url='login')
def accept_invite(request, invite_id):
    inv = get_object_or_404(GroupInvite, id=invite_id, invitee=request.user)
    group = inv.group
    inviter = inv.invited_by  # save before delete
    if request.method == 'POST':
        group.members.add(request.user)
        inv.delete()
        layer = get_channel_layer()
        names = sorted([inviter.username, request.user.username])
        room = f'private_{names[0]}_{names[1]}'
        async_to_sync(layer.group_send)(room, {'type': 'chat.invite_response', 'invite_id': invite_id, 'accepted': True, 'group_id': group.id, 'group_name': group.name, 'user': request.user.username})
        return JsonResponse({'ok': True})
    group.members.add(request.user)
    inv.delete()
    return redirect('group-view', group_id=group.id)


@login_required(login_url='login')
def decline_invite(request, invite_id):
    inv = get_object_or_404(GroupInvite, id=invite_id, invitee=request.user)
    group = inv.group
    inviter = inv.invited_by  # save before delete
    inv.delete()
    if request.method == 'POST':
        layer = get_channel_layer()
        names = sorted([inviter.username, request.user.username])
        room = f'private_{names[0]}_{names[1]}'
        async_to_sync(layer.group_send)(room, {'type': 'chat.invite_response', 'invite_id': invite_id, 'accepted': False, 'group_id': group.id, 'group_name': group.name, 'user': request.user.username})
        return JsonResponse({'ok': True})
    return redirect('users-list')


@login_required(login_url='login')
def private_chat(request, username):
    try:
        other = User.objects.select_related('profile').get(profile__username=username)
    except User.DoesNotExist:
        try:
            other = User.objects.select_related('profile').get(username=username)
        except User.DoesNotExist:
            return redirect('users-list')
    blocked_by_other = is_blocked(other, request.user)
    i_blocked = is_blocked(request.user, other)
    friends = is_friend(request.user, other)
    # Only private groups the user is a member of can be used for invites
    my_private_groups = Group.objects.filter(members=request.user, private=True)

    from chat.models import PrivateMessage, GroupInvite
    from django.db.models import Q
    messages_qs = PrivateMessage.objects.filter(
        Q(from_user=request.user, to_user=other) | Q(from_user=other, to_user=request.user)
    ).select_related('from_user__profile').order_by('-created_at')[:50]

    pending_invites = GroupInvite.objects.filter(
        Q(invited_by=request.user, invitee=other) | Q(invited_by=other, invitee=request.user)
    ).select_related('group', 'invited_by', 'invitee')

    return render(request, 'private_chat.html', {
        'other': other,
        'blocked_by_other': blocked_by_other,
        'i_blocked': i_blocked,
        'friends': friends,
        'my_private_groups': my_private_groups,
        'messages': reversed(list(messages_qs)),
        'pending_invites': pending_invites,
    })


@login_required(login_url='login')
@require_POST
def toggle_friend(request, username):
    try:
        other = User.objects.get(profile__username=username)
    except User.DoesNotExist:
        try:
            other = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponseBadRequest('user not found')

    if is_blocked(other, request.user) or is_blocked(request.user, other):
        return JsonResponse({'ok': False, 'error': 'blocked'})

    if is_friend(request.user, other):
        with transaction.atomic():
            remove_friend(request.user, other)
        # notify group (if chat open) about friend change
        layer = get_channel_layer()
        names = sorted([request.user.username, other.username])
        room = f'private_{names[0]}_{names[1]}'
        async_to_sync(layer.group_send)(room, {'type': 'chat.state', 'friends': False, 'blocked': False, 'actor': request.user.username})
        return JsonResponse({'ok': True, 'friends': False})
    else:
        with transaction.atomic():
            add_friend(request.user, other)
        layer = get_channel_layer()
        names = sorted([request.user.username, other.username])
        room = f'private_{names[0]}_{names[1]}'
        async_to_sync(layer.group_send)(room, {'type': 'chat.state', 'friends': True, 'blocked': False, 'actor': request.user.username})
        return JsonResponse({'ok': True, 'friends': True})


@login_required(login_url='login')
@require_POST
def toggle_block(request, username):
    try:
        other = User.objects.get(profile__username=username)
    except User.DoesNotExist:
        try:
            other = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponseBadRequest('user not found')

    if is_blocked(request.user, other):
        with transaction.atomic():
            unblock_user(request.user, other)
        layer = get_channel_layer()
        names = sorted([request.user.username, other.username])
        room = f'private_{names[0]}_{names[1]}'
        async_to_sync(layer.group_send)(room, {'type': 'chat.state', 'blocked': False, 'friends': is_friend(request.user, other), 'actor': request.user.username})
        return JsonResponse({'ok': True, 'blocked': False})
    else:
        with transaction.atomic():
            block_user(request.user, other)
        layer = get_channel_layer()
        names = sorted([request.user.username, other.username])
        room = f'private_{names[0]}_{names[1]}'
        async_to_sync(layer.group_send)(room, {'type': 'chat.state', 'blocked': True, 'friends': False, 'actor': request.user.username})
        return JsonResponse({'ok': True, 'blocked': True})


@login_required(login_url='login')
@require_POST
def join_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if group.private:
        return HttpResponseBadRequest('group is private')
    group.members.add(request.user)
    return redirect('group-view', group_id=group.id)
