from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from room.consumers import room_users

ALLOWED_ROOMS = [f'lobby-{i}' for i in range(1, 11)]

@login_required(login_url='login')
def index(request):
    rooms = []
    for name in ALLOWED_ROOMS:
        group_name = f'chat_{name}'
        online = len(room_users.get(group_name, set()))
        rooms.append({'name': name, 'online': online})
    return render(request, "room/index.html", {"rooms": rooms})

@login_required(login_url='login')
def room(request, room_name):
    if room_name not in ALLOWED_ROOMS:
        return redirect('room-index')
    return render(request, "room/room.html", {"room_name": room_name})
