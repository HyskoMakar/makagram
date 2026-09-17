from django import template

register = template.Library()

@register.inclusion_tag('components/username.html')
def username(user):
    if not user:
        return {
            'username': '',
            'color': 'gray',
            'suffix': '',
        }

    profile = getattr(user, 'profile', None)

    if profile:
        display_name = profile.display_name
        color = profile.color or 'gray'

        achievement = getattr(
            profile,
            'equipped_achievement',
            None,
        )

        suffix = (
            achievement.suffix
            if achievement
            else ''
        )
    else:
        display_name = user.username
        color = 'gray'
        suffix = ''

    return {
        'username': display_name,
        'color': color,
        'suffix': suffix,
    }