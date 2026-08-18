from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import LoginForm, RegisterForm
from .models import ALLOWED_COLORS, DEFAULT_COLOR

def index(request):
    return render(request, "base.html")

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

def logout_view(request):
    logout(request)
    return redirect('login')

def profile_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    profile = request.user.profile

    if profile.color not in ALLOWED_COLORS:
        profile.color = DEFAULT_COLOR
        profile.save()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', DEFAULT_COLOR)

        if username:
            profile.username = username
        if description:
            profile.description = description
        profile.color = color if color in ALLOWED_COLORS else DEFAULT_COLOR

        if 'clear_avatar' in request.POST and profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
        elif 'avatar' in request.FILES:
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = request.FILES['avatar']

        profile.save()
        return redirect('profile')

    return render(request, 'profile.html', {'profile': profile, 'colors': ALLOWED_COLORS})
