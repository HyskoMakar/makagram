from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .consumers import ALLOWED_ROOMS, room_users


@login_required(login_url='login')
def index(request):
    rooms = [
        {
            'name': name,
            'online': len(room_users.get(f'chat_{name}', set())),
        }
        for name in ALLOWED_ROOMS
    ]
    return render(request, 'lobbies.html', {'rooms': rooms})


@login_required(login_url='login')
def room(request, room_name):
    if room_name not in ALLOWED_ROOMS:
        return redirect('room-index')
    return render(request, 'lobby.html', {'room_name': room_name})
