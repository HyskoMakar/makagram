from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .models import Achievement, UserAchievement

DEFAULT_ACHIEVEMENTS = [
    {
        'key': 'welcome',
        'name': 'Welcome',
        'description': 'Register in the app.',
        'suffix': 'new',
        'icon': '🎉',
        'is_super': False,
        'check': lambda user, ctx: True,
    },
    {
        'key': 'first_message',
        'name': 'First Message',
        'description': 'Send your first message.',
        'suffix': 'speaker',
        'icon': '💬',
        'is_super': False,
        'check': lambda user, ctx: ctx['total_messages'] >= 1,
    },
    {
        'key': 'first_friend',
        'name': 'First Friend',
        'description': 'Add your first friend.',
        'suffix': 'buddy',
        'icon': '🤝',
        'is_super': False,
        'check': lambda user, ctx: ctx['friend_count'] >= 1,
    },
    {
        'key': 'first_group',
        'name': 'Group Starter',
        'description': 'Join or create your first group.',
        'suffix': 'host',
        'icon': '🏠',
        'is_super': False,
        'check': lambda user, ctx: ctx['group_count'] >= 1,
    },
    {
        'key': 'first_channel',
        'name': 'Channel Starter',
        'description': 'Join or create your first channel.',
        'suffix': 'channel',
        'icon': '📣',
        'is_super': False,
        'check': lambda user, ctx: ctx['channel_count'] >= 1,
    },
    {
        'key': 'chatter',
        'name': 'Chatter',
        'description': 'Send 5 messages in total.',
        'suffix': 'chatter',
        'icon': '🗣️',
        'is_super': False,
        'check': lambda user, ctx: ctx['total_messages'] >= 5,
    },
    {
        'key': 'social_butterfly',
        'name': 'Social Butterfly',
        'description': 'Add 3 friends.',
        'suffix': 'buzz',
        'icon': '🦋',
        'is_super': False,
        'check': lambda user, ctx: ctx['friend_count'] >= 3,
    },
    {
        'key': 'group_member',
        'name': 'Group Member',
        'description': 'Join 2 groups.',
        'suffix': 'crew',
        'icon': '👥',
        'is_super': False,
        'check': lambda user, ctx: ctx['group_count'] >= 2,
    },
    {
        'key': 'channel_member',
        'name': 'Channel Member',
        'description': 'Join 2 channels.',
        'suffix': 'fan',
        'icon': '📺',
        'is_super': False,
        'check': lambda user, ctx: ctx['channel_count'] >= 2,
    },
    {
        'key': 'creator',
        'name': 'Creator',
        'description': 'Create 3 posts or messages.',
        'suffix': 'creator',
        'icon': '🎨',
        'is_super': False,
        'check': lambda user, ctx: ctx['total_messages'] >= 3,
    },
    {
        'key': 'helper',
        'name': 'Private speaker',
        'description': 'Write a message to another user.',
        'suffix': 'private person',
        'icon': '🛟',
        'is_super': False,
        'check': lambda user, ctx: ctx['total_messages'] >= 1,
    },
    {
        'key': 'collector',
        'name': 'Collector',
        'description': 'Unlock 5 achievements.',
        'suffix': 'collector',
        'icon': '📦',
        'is_super': False,
        'check': lambda user, ctx: ctx['unlocked_count'] >= 5,
    },
    {
        'key': 'trendsetter',
        'name': 'Trendsetter',
        'description': 'Use a nickname longer than 8 characters.',
        'suffix': 'trend',
        'icon': '✨',
        'is_super': False,
        'check': lambda user, ctx: len(ctx['profile_name']) >= 8,
    },
    {
        'key': 'lobby_lurker',
        'name': 'Lobby Lurker',
        'description': 'Log in late at night or early morning.',
        'suffix': 'owl',
        'icon': '🦉',
        'is_super': False,
        'check': lambda user, ctx: ctx['last_login'].hour >= 22 or ctx['last_login'].hour < 4,
    },
    {
        'key': 'veteran',
        'name': 'Veteran',
        'description': 'Stay active for at least 7 days.',
        'suffix': 'veteran',
        'icon': '🏅',
        'is_super': False,
        'check': lambda user, ctx: timezone.now() - user.date_joined >= timedelta(days=7),
    },
    {
        'key': 'explorer',
        'name': 'Explorer',
        'description': 'Use chats, groups and channels.',
        'suffix': 'explorer',
        'icon': '🧭',
        'is_super': False,
        'check': lambda user, ctx: ctx['total_messages'] >= 1 and ctx['group_count'] >= 1 and ctx['channel_count'] >= 1,
    },
    {
        'key': 'legend',
        'name': 'Legend',
        'description': 'Unlock 10 achievements.',
        'suffix': 'legend',
        'icon': '👑',
        'is_super': False,
        'check': lambda user, ctx: ctx['unlocked_count'] >= 10,
    },
    {
        'key': 'mastermind',
        'name': 'Mastermind',
        'description': 'Unlock 15 achievements.',
        'suffix': 'master',
        'icon': '🧠',
        'is_super': False,
        'check': lambda user, ctx: ctx['unlocked_count'] >= 15,
    },
    {
        'key': 'superuser',
        'name': 'Superuser',
        'description': 'Be a Django superuser.',
        'suffix': 'admin',
        'icon': '🛡️',
        'is_super': True,
        'check': lambda user, ctx: user.is_superuser,
    },
    {
        'key': 'popular',
        'name': 'Popular',
        'description': 'Have 100 subscribers on your channel.',
        'suffix': 'popular',
        'icon': '📈',
        'is_super': True,
        'check': lambda user, ctx: ctx['has_popular_channel'],
    },
    {
        'key': 'lover',
        'name': 'Lover',
        'description': 'Put 200 likes on different posts.',
        'suffix': 'lover',
        'icon': '💖',
        'is_super': True,
        'check': lambda user, ctx: ctx['total_likes'] >= 200,
    },
    {
        'key': 'spammer',
        'name': 'Spammer',
        'description': 'Send 1000 messages in one section without counting repeated consecutive identical messages.',
        'suffix': 'spam',
        'icon': '📨',
        'is_super': True,
        'check': lambda user, ctx: ctx['total_messages'] >= 1000,
    },
    {
        'key': 'worst',
        'name': 'Worst',
        'description': 'Be blocked by 50 users.',
        'suffix': 'banned',
        'icon': '🚫',
        'is_super': True,
        'check': lambda user, ctx: ctx['blocked_by_users'] >= 50,
    },
    {
        'key': 'administration',
        'name': 'Administration',
        'description': 'Be an admin in 10 channels owned by different users, each older than 7 days.',
        'suffix': 'staff',
        'icon': '🧑‍💼',
        'is_super': True,
        'check': lambda user, ctx: ctx['admin_in_other_channels'] >= 10,
    },
    {
        'key': 'achiever',
        'name': 'Achiever',
        'description': 'Unlock all regular achievements.',
        'suffix': 'achiever',
        'icon': '🏆',
        'is_super': True,
        'check': lambda user, ctx: ctx['regular_unlocked_keys'] >= ctx['regular_keys'],
    },
    {
        'key': 'superperson',
        'name': 'Superperson',
        'description': 'Complete all super challenges.',
        'suffix': 'super',
        'icon': '🌟',
        'is_super': True,
        'check': lambda user, ctx: ctx['required_super_keys'].issubset(ctx['unlocked_keys']),
    },
]


def ensure_default_achievements():
    for data in DEFAULT_ACHIEVEMENTS:
        Achievement.objects.update_or_create(
            key=data['key'],
            defaults={
                'name': data['name'],
                'description': data['description'],
                'suffix': data['suffix'],
                'icon': data['icon'],
                'is_super': data.get('is_super', False),
                'is_active': True,
            },
        )
    return Achievement.objects.filter(is_active=True).count()


def unlock_achievement(user, key):
    if not user or not user.is_authenticated:
        return False

    achievement = Achievement.objects.filter(key=key, is_active=True).first()
    if not achievement:
        return False

    _, created = UserAchievement.objects.get_or_create(user=user, achievement=achievement)
    return created


def _count_valid_spam_messages(user):
    from channel.models import ChannelPost
    from chat.models import GroupMessage, PrivateMessage

    entries = []
    for post in ChannelPost.objects.filter(author=user).values('created_at', 'content'):
        entries.append((post['created_at'], post['content'], 'channel'))
    for msg in GroupMessage.objects.filter(author=user).values('created_at', 'content', 'group_id'):
        entries.append((msg['created_at'], msg['content'], f'group_{msg["group_id"]}'))
    for msg in PrivateMessage.objects.filter(from_user=user).values('created_at', 'content', 'to_user_id'):
        entries.append((msg['created_at'], msg['content'], f'private_{msg["to_user_id"]}'))

    entries.sort(key=lambda item: item[0])

    valid_count = 0
    previous_content = None
    previous_section = None
    previous_time = None

    for created_at, content, section in entries:
        if content is None:
            continue

        is_repeated_consecutive_duplicate = (
            previous_content is not None
            and content == previous_content
            and section == previous_section
            and previous_time is not None
            and created_at - previous_time <= timedelta(minutes=5)
        )

        if is_repeated_consecutive_duplicate:
            previous_time = created_at
            continue

        valid_count += 1
        previous_content = content
        previous_section = section
        previous_time = created_at

    return valid_count

def maybe_unlock_for_user(user):
    if not user or not user.is_authenticated:
        return []

    from channel.models import Channel, ChannelPostLike
    from chat.models import Block, Friendship, Group, PrivateMessage

    profile = getattr(user, 'profile', None)

    valid_spam_count = _count_valid_spam_messages(user)

    ctx = {
        'total_messages': valid_spam_count,
        'friend_count': Friendship.objects.filter(user=user).count(),
        'group_count': Group.objects.filter(members=user).count(),
        'channel_count': Channel.objects.filter(subscribers=user).count(),
        'total_likes': ChannelPostLike.objects.filter(creator=user).count(),
        'blocked_by_users': Block.objects.filter(blocked=user).count(),
        'admin_in_other_channels': Channel.objects.filter(
            admins=user, owner__isnull=False
        ).exclude(owner=user).filter(
            created_at__lt=timezone.now() - timedelta(days=7)
        ).values_list('owner_id', flat=True).distinct().count(),
        'unlocked_count': UserAchievement.objects.filter(user=user).count(),
        'profile_name': (profile.username if profile and hasattr(profile, 'username') else user.username).strip(),
        'last_login': user.last_login or user.date_joined,
        'has_popular_channel': Channel.objects.filter(owner=user).annotate(
            sub_count=models.Count('subscribers')
        ).filter(sub_count__gte=100).exists(),
        'regular_keys': set(
            Achievement.objects.filter(is_super=False).exclude(key='achiever').values_list('key', flat=True)
        ),
        'regular_unlocked_keys': set(
            UserAchievement.objects.filter(user=user, achievement__is_super=False).exclude(achievement__key='achiever').values_list('achievement__key', flat=True)
        ),
        'required_super_keys': {'superuser', 'popular', 'lover', 'spammer', 'worst', 'administration', 'achiever'},
        'unlocked_keys': set(UserAchievement.objects.filter(user=user).values_list('achievement__key', flat=True)),
    }

    unlocked = []
    for item in DEFAULT_ACHIEVEMENTS:
        key = item['key']
        check_func = item.get('check')

        if check_func and check_func(user, ctx):
            if unlock_achievement(user, key):
                unlocked.append(key)
                
                ctx['unlocked_count'] += 1
                ctx['unlocked_keys'].add(key)
                if not item.get('is_super') and key != 'achiever':
                    ctx['regular_unlocked_keys'].add(key)

    return unlocked