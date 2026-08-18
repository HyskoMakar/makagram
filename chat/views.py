from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User


@login_required(login_url='login')
def users_list(request):
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    return render(request, 'chat/users.html', {'users': users})


@login_required(login_url='login')
def private_chat(request, username):
    try:
        other = User.objects.select_related('profile').get(profile__username=username)
    except User.DoesNotExist:
        try:
            other = User.objects.select_related('profile').get(username=username)
        except User.DoesNotExist:
            return redirect('users-list')
    return render(request, 'chat/private.html', {'other': other})
