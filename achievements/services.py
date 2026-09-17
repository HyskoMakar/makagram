from .models import Achievement, UserAchievement


def unlock_achievement(user, key):
    if not user or not user.is_authenticated:
        return False

    achievement = Achievement.objects.filter(
        key=key,
        is_active=True,
    ).first()

    if not achievement:
        return False

    _, created = UserAchievement.objects.get_or_create(
        user=user,
        achievement=achievement,
    )

    return created