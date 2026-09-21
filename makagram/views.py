import re
import pyotp
import qrcode
from io import BytesIO

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from achievements.services import maybe_unlock_for_user, unlock_achievement

from .forms import LoginForm, RegisterForm
from .models import ALLOWED_COLORS, DEFAULT_COLOR, Profile

MAX_AVATAR_SIZE = 5 * 1024 * 1024
MAX_AVATAR_DIMENSION = 2000

def index_view(request):
    return render(request, 'index.html')

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

            login(request, user)
            maybe_unlock_for_user(user)
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
            maybe_unlock_for_user(user)
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
        unlock_achievement(user, 'welcome')
        login(request, user)
        maybe_unlock_for_user(user)
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
        unlock_achievement(request.user, 'profile_setup')
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