from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from makagram.models import is_friend, add_friend, remove_friend, is_blocked, block_user, unblock_user
from django.core.cache import cache


@login_required(login_url='login')
def users_list(request):
    tab = request.GET.get('tab', 'all')
    if tab == 'friends':
        # get friends of current user
        from makagram.models import Friendship
        friend_ids = Friendship.objects.filter(user=request.user).values_list('friend_id', flat=True)
        users = User.objects.filter(id__in=friend_ids).select_related('profile')
    else:
        users = User.objects.exclude(id=request.user.id).select_related('profile')
    # build cache keys and check who is online
    keys = {f'online_user_{u.id}': u.id for u in users}
    online_map = cache.get_many(list(keys.keys()))
    online_ids = {keys[k] for k in online_map.keys()}
    return render(request, 'chat/users.html', {'users': users, 'tab': tab, 'online_ids': online_ids})


@login_required(login_url='login')
def private_chat(request, username):
    try:
        other = User.objects.select_related('profile').get(profile__username=username)
    except User.DoesNotExist:
        try:
            other = User.objects.select_related('profile').get(username=username)
        except User.DoesNotExist:
            return redirect('users-list')
    # relationship statuses
    blocked_by_other = is_blocked(other, request.user)
    i_blocked = is_blocked(request.user, other)
    friends = is_friend(request.user, other)
    return render(request, 'chat/private.html', {'other': other, 'blocked_by_other': blocked_by_other, 'i_blocked': i_blocked, 'friends': friends})


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

    # cannot friend if blocked one-way
    if is_blocked(other, request.user) or is_blocked(request.user, other):
        return JsonResponse({'ok': False, 'error': 'blocked'})

    if is_friend(request.user, other):
        remove_friend(request.user, other)
        return JsonResponse({'ok': True, 'friends': False})
    else:
        add_friend(request.user, other)
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
        unblock_user(request.user, other)
        return JsonResponse({'ok': True, 'blocked': False})
    else:
        # blocking removes friendship
        block_user(request.user, other)
        return JsonResponse({'ok': True, 'blocked': True})
