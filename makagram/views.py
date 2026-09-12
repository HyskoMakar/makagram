import re
import pyotp
import qrcode
from io import BytesIO
from datetime import timedelta

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from channel.models import ChannelPost
from chat.models import Group, GroupMessage, PrivateMessage
from notifications.models import Notification

from .forms import LoginForm, RegisterForm
from .models import ALLOWED_COLORS, DEFAULT_COLOR, Profile

MAX_AVATAR_SIZE = 5 * 1024 * 1024
MAX_AVATAR_DIMENSION = 2000

@login_required(login_url='login')
def index_view(request):
    return render(request, 'index.html')


@login_required(login_url='login')
def admin_abuse_page_view(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Only admins can access abuse page!')

    stats = {
        'total_users': User.objects.count(),
        'total_private_messages': PrivateMessage.objects.count(),
        'total_group_messages': GroupMessage.objects.count(),
        'total_channel_posts': ChannelPost.objects.count(),
        'total_groups': Group.objects.count(),
        'total_broadcasts': Notification.objects.filter(recipient__isnull=True, notification_type='system').count(),
        'active_last_7_days': User.objects.filter(last_login__gte=timezone.now() - timedelta(days=7)).count(),
        'active_users_today': User.objects.filter(last_login__gte=timezone.now() - timedelta(days=1)).count(),
    }

    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()[:255]
        message = (request.POST.get('message') or '').strip()
        link = ''

        if not title or not message:
            return render(request, 'admin_abuse_page.html', {
                'error': 'Title and message are required.',
                'title': title,
                'message': message,
                'stats': stats,
            })

        match = re.search(r'https?://\S+|/\S+', message)
        if match:
            link = match.group(0)[:255]

        Notification.objects.create(
            recipient=None,
            sender=request.user,
            title=title,
            message=message,
            notification_type='system',
            link=link,
        )
        return redirect('admin-abuse')

    return render(request, 'admin_abuse_page.html', {'stats': stats})


def guide_view(request):
    return render(request, 'guide.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    form = LoginForm(data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            profile = getattr(user, 'profile', None)

            if profile and profile.mfa_enabled:
                if not 'mfa_token' in request.POST:
                    request.session['pre_mfa_user_id'] = user.id

                    return redirect('verify_mfa_login')
                else:
                    login(request, user)
                    return redirect('index')
                
    return render(request, 'login.html', {'form': form})

def verify_mfa_login(request):
    user_id = request.session.get('pre_mfa_user_id')
    if not user_id:
        return redirect('login')
        
    user = User.objects.get(id=user_id)
    
    if request.method == "POST":
        user_code = request.POST.get("otp_code")
        totp = pyotp.TOTP(user.profile.mfa_secret)
        
        if totp.verify(user_code):
            login(request, user)
            del request.session['pre_mfa_user_id']
            return redirect('index')
        else:
            messages.error(request, "Incorrect. Try again")
            
    return render(request, "verify_mfa_login.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect('feed')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('feed')
    return render(request, 'register.html', {'form': form})


@login_required(login_url='login')
def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')


@login_required(login_url='login')
def profile_view(request):
    profile = request.user.profile

    if profile.color not in ALLOWED_COLORS:
        profile.color = DEFAULT_COLOR
        profile.save(update_fields=['color'])

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()[:50]
        description = request.POST.get('description', '').strip()[:50]
        color = request.POST.get('color', DEFAULT_COLOR)

        if username and re.fullmatch(r'[A-Za-z0-9_-]{1,50}', username):
            profile.username = username
        elif username:
            return render(request, 'profile.html', {
                'profile': profile,
                'colors': ALLOWED_COLORS,
                'error': 'Nickname can contain only letters, numbers, _ and -.',
            })
        profile.description = description
        profile.color = color if color in ALLOWED_COLORS else DEFAULT_COLOR

        if 'clear_avatar' in request.POST:
            profile.avatar_data = None
            profile.avatar_type = ''

            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None

        elif 'avatar' in request.FILES:
            avatar = request.FILES['avatar']

            if avatar.size > 2 * 1024 * 1024:
                return render(request, 'profile.html', {
                    'profile': profile,
                    'colors': ALLOWED_COLORS,
                    'error': 'Avatar must be smaller than 2 MB.'
                })

            profile.avatar_data = avatar.read()
            profile.avatar_type = avatar.content_type

            if profile.avatar:
                profile.avatar.delete(save=False)
                profile.avatar = None

        profile.save()
        return redirect('profile')

    return render(request, 'profile.html', {
        'profile': profile,
        'colors': ALLOWED_COLORS,
    })


def avatar_view(request, user_id):
    from django.contrib.auth.models import User

    try:
        profile = User.objects.get(id=user_id).profile
    except User.DoesNotExist:
        return HttpResponse(status=404)

    if not profile.avatar_data:
        return HttpResponse(status=404)

    return HttpResponse(
        profile.avatar_data,
        content_type=profile.avatar_type or 'image/jpeg'
    )

@login_required
def generate_qr_code(request):
    user_profile, created = Profile.objects.get_or_create(user=request.user)

    totp = pyotp.TOTP(user_profile.mfa_secret)
    auth_url = totp.provisioning_uri(name=request.user.email, issuer_name="MaKaGram")

    img = qrcode.make(auth_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    
    return HttpResponse(buffer.getvalue(), content_type="image/png")

def verify_mfa(request):
    if request.method == "POST":
        user_code = request.POST.get("otp_code")
        user_profile = request.user.profile
        
        totp = pyotp.TOTP(user_profile.mfa_secret)
        
        if totp.verify(user_code):
            user_profile.mfa_enabled = True
            user_profile.save()
            return redirect('index')
        else:
            messages.error(request, "Invalid authentication token. Try again.")
            
    return render(request, "verify_mfa.html")

@login_required
def setup_mfa_view(request):
    return render(request, 'setup_mfa.html')

@login_required
def remove_mfa(request):
    user_profile = request.user.profile
    user_profile.mfa_enabled = False
    user_profile.save()
    
    return redirect('profile')