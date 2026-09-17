from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import Achievement, UserAchievement


@login_required(login_url='login')
def achievements_list(request):
    achievements = Achievement.objects.filter(
        is_active=True
    ).order_by('id')

    unlocked_ids = set(
        UserAchievement.objects.filter(
            user=request.user,
            achievement__is_active=True,
        ).values_list(
            'achievement_id',
            flat=True,
        )
    )

    equipped_id = None

    profile = getattr(request.user, 'profile', None)

    if profile and profile.equipped_achievement_id:
        equipped_id = profile.equipped_achievement_id

    return render(
        request,
        'achievements.html',
        {
            'achievements': achievements,
            'unlocked_ids': unlocked_ids,
            'equipped_id': equipped_id,
        },
    )


@login_required(login_url='login')
@require_POST
def equip_achievement(request, achievement_id):
    profile = getattr(request.user, 'profile', None)

    if profile is None:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Profile not found',
            },
            status=400,
        )

    try:
        achievement = Achievement.objects.get(
            id=achievement_id,
            is_active=True,
        )
    except Achievement.DoesNotExist:
        raise Http404

    unlocked = UserAchievement.objects.filter(
        user=request.user,
        achievement=achievement,
    ).exists()

    if not unlocked:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Achievement is not unlocked',
            },
            status=403,
        )

    profile.equipped_achievement = achievement
    profile.save(
        update_fields=['equipped_achievement']
    )

    return JsonResponse(
        {
            'ok': True,
            'achievement_id': achievement.id,
            'suffix': achievement.suffix,
        }
    )


@login_required(login_url='login')
@require_POST
def unequip_achievement(request):
    profile = getattr(request.user, 'profile', None)

    if profile is None:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Profile not found',
            },
            status=400,
        )

    profile.equipped_achievement = None
    profile.save(
        update_fields=['equipped_achievement']
    )

    return JsonResponse(
        {
            'ok': True,
        }
    )