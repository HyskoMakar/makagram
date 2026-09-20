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
        if achievement is not None:
            if achievement.type == 'super':
                suffix_color = 'amber'
            elif achievement.type == 'ultra':
                suffix_color = 'purple'
            else:
                suffix_color = 'gray'
        else:
            suffix_color = 'gray'

    else:
        display_name = user.username
        color = 'gray'
        suffix = ''
        suffix_color = 'gray'

    return {
        'username': display_name,
        'color': color,
        'suffix': suffix,
        'suffix_color': suffix_color,
    }