from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import LoginForm, RegisterForm

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
