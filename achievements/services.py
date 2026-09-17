from datetime import timedelta

from django.db import models
from django.utils import timezone

from .models import Achievement, UserAchievement

DEFAULT_ACHIEVEMENTS = [
    {'key': 'welcome', 'name': 'Welcome', 'description': 'Register in the app.', 'suffix': 'new', 'icon': '🎉', 'is_super': False},
    {'key': 'profile_setup', 'name': 'Profile Setup', 'description': 'Set a custom nickname and profile color.', 'suffix': 'profiler', 'icon': '👤', 'is_super': False},
    {'key': 'first_message', 'name': 'First Message', 'description': 'Send your first message.', 'suffix': 'speaker', 'icon': '💬', 'is_super': False},
    {'key': 'first_friend', 'name': 'First Friend', 'description': 'Add your first friend.', 'suffix': 'buddy', 'icon': '🤝', 'is_super': False},
    {'key': 'first_group', 'name': 'Group Starter', 'description': 'Join or create your first group.', 'suffix': 'host', 'icon': '🏠', 'is_super': False},
    {'key': 'first_channel', 'name': 'Channel Starter', 'description': 'Join or create your first channel.', 'suffix': 'channel', 'icon': '📣', 'is_super': False},
    {'key': 'chatter', 'name': 'Chatter', 'description': 'Send 5 messages in total.', 'suffix': 'chatter', 'icon': '🗣️', 'is_super': False},
    {'key': 'social_butterfly', 'name': 'Social Butterfly', 'description': 'Add 3 friends.', 'suffix': 'buzz', 'icon': '🦋', 'is_super': False},
    {'key': 'group_member', 'name': 'Group Member', 'description': 'Join 2 groups.', 'suffix': 'crew', 'icon': '👥', 'is_super': False},
    {'key': 'channel_member', 'name': 'Channel Member', 'description': 'Join 2 channels.', 'suffix': 'fan', 'icon': '📺', 'is_super': False},
    {'key': 'creator', 'name': 'Creator', 'description': 'Create 3 posts or messages.', 'suffix': 'creator', 'icon': '🎨', 'is_super': False},
    {'key': 'helper', 'name': 'Private speaker', 'description': 'Write a message to another user.', 'suffix': 'private person', 'icon': '🛟', 'is_super': False},
    {'key': 'collector', 'name': 'Collector', 'description': 'Unlock 5 achievements.', 'suffix': 'collector', 'icon': '📦', 'is_super': False},
    {'key': 'trendsetter', 'name': 'Trendsetter', 'description': 'Use a nickname longer than 8 characters.', 'suffix': 'trend', 'icon': '✨', 'is_super': False},
    {'key': 'lobby_lurker', 'name': 'Lobby Lurker', 'description': 'Log in late at night or early morning.', 'suffix': 'owl', 'icon': '🦉', 'is_super': False},
    {'key': 'feed_reader', 'name': 'Feed Reader', 'description': 'Visit the community feed.', 'suffix': 'feed', 'icon': '📰', 'is_super': False},
    {'key': 'veteran', 'name': 'Veteran', 'description': 'Stay active for at least 7 days.', 'suffix': 'veteran', 'icon': '🏅', 'is_super': False},
    {'key': 'explorer', 'name': 'Explorer', 'description': 'Use chats, groups and channels.', 'suffix': 'explorer', 'icon': '🧭', 'is_super': False},
    {'key': 'legend', 'name': 'Legend', 'description': 'Unlock 10 achievements.', 'suffix': 'legend', 'icon': '👑', 'is_super': False},
    {'key': 'mastermind', 'name': 'Mastermind', 'description': 'Unlock 15 achievements.', 'suffix': 'master', 'icon': '🧠', 'is_super': False},
    {'key': 'achiever', 'name': 'Achiever', 'description': 'Unlock all regular achievements.', 'suffix': 'achiever', 'icon': '🏆', 'is_super': True},
    {'key': 'superuser', 'name': 'Superuser', 'description': 'Be a Django superuser.', 'suffix': 'admin', 'icon': '🛡️', 'is_super': True},
    {'key': 'popular', 'name': 'Popular', 'description': 'Have 100 subscribers on your channel.', 'suffix': 'popular', 'icon': '📈', 'is_super': True},
    {'key': 'lover', 'name': 'Lover', 'description': 'Put 200 likes on different posts.', 'suffix': 'lover', 'icon': '💖', 'is_super': True},
    {'key': 'spammer', 'name': 'Spammer', 'description': 'Send 1000 messages in one section without counting repeated consecutive identical messages.', 'suffix': 'spam', 'icon': '📨', 'is_super': True},
    {'key': 'worst', 'name': 'Worst', 'description': 'Be blocked by 50 users.', 'suffix': 'banned', 'icon': '🚫', 'is_super': True},
    {'key': 'administration', 'name': 'Administration', 'description': 'Be an admin in 10 channels owned by different users, each older than 7 days.', 'suffix': 'staff', 'icon': '🧑‍💼', 'is_super': True},
    {'key': 'superperson', 'name': 'Superperson', 'description': 'Complete all super challenges.', 'suffix': 'super', 'icon': '🌟', 'is_super': True},
]


def ensure_default_achievements():
    for data in DEFAULT_ACHIEVEMENTS:
        Achievement.objects.get_or_create(
            key=data['key'],
            defaults={
                'name': data['name'],
                'description': data['description'],
                'suffix': data['suffix'],
                'icon': data['icon'],
                'is_active': True,
            },
        )

    for data in DEFAULT_ACHIEVEMENTS:
        Achievement.objects.filter(key=data['key']).update(is_super=data.get('is_super', False))

    return Achievement.objects.filter(is_active=True).count()


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

    from channel.models import Channel, ChannelPost, ChannelPostLike
    from chat.models import Block, Friendship, Group, GroupMessage, PrivateMessage

    profile = getattr(user, 'profile', None)
    total_messages = (
        PrivateMessage.objects.filter(from_user=user).count()
        + GroupMessage.objects.filter(author=user).count()
        + ChannelPost.objects.filter(author=user).count()
    )
    friend_count = Friendship.objects.filter(user=user).count()
    group_count = Group.objects.filter(members=user).count()
    channel_count = Channel.objects.filter(subscribers=user).count()
    total_likes = ChannelPostLike.objects.filter(creator=user).count()
    blocked_by_users = Block.objects.filter(blocked=user).count()
    old_admin_channel_owners = Channel.objects.filter(
        admins=user,
        owner__isnull=False,
    ).exclude(owner=user).filter(
        created_at__lt=timezone.now() - timedelta(days=7),
    ).values_list('owner_id', flat=True).distinct()
    admin_in_other_channels = old_admin_channel_owners.count()
    unlocked_count = UserAchievement.objects.filter(user=user).count()
    profile_name = (profile.username if profile else '').strip()
    last_login = user.last_login or user.date_joined
    has_popular_channel = Channel.objects.filter(owner=user).annotate(sub_count=models.Count('subscribers')).filter(sub_count__gte=100).exists()
    valid_spam_count = _count_valid_spam_messages(user)
    regular_keys = set(
        Achievement.objects.filter(is_super=False).exclude(key='achiever').values_list('key', flat=True)
    )
    regular_unlocked_keys = set(
        UserAchievement.objects.filter(user=user, achievement__is_super=False).exclude(achievement__key='achiever').values_list('achievement__key', flat=True)
    )
    required_super_keys = {'superuser', 'popular', 'lover', 'spammer', 'worst', 'administration', 'achiever'}

    checks = [
        ('welcome', True),
        ('profile_setup', bool(profile and profile_name)),
        ('first_message', total_messages >= 1),
        ('first_friend', friend_count >= 1),
        ('first_group', group_count >= 1),
        ('first_channel', channel_count >= 1),
        ('chatter', total_messages >= 5),
        ('social_butterfly', friend_count >= 3),
        ('group_member', group_count >= 2),
        ('channel_member', channel_count >= 2),
        ('creator', total_messages >= 3),
        ('helper', total_messages >= 1),
        ('collector', unlocked_count >= 5),
        ('trendsetter', len(profile_name) >= 8),
        ('lobby_lurker', last_login.hour >= 22 or last_login.hour < 4),
        ('feed_reader', True),
        ('veteran', timezone.now() - user.date_joined >= timedelta(days=7)),
        ('explorer', total_messages >= 1 and group_count >= 1 and channel_count >= 1),
        ('legend', unlocked_count >= 10),
        ('mastermind', unlocked_count >= 15),
        ('superuser', user.is_superuser),
        ('popular', has_popular_channel),
        ('lover', total_likes >= 200),
        ('spammer', valid_spam_count >= 1000),
        ('worst', blocked_by_users >= 50),
        ('administration', admin_in_other_channels >= 10),
        ('achiever', regular_unlocked_keys >= regular_keys),
    ]

    unlocked = []
    for key, condition in checks:
        if condition and unlock_achievement(user, key):
            unlocked.append(key)

    unlocked_keys = set(UserAchievement.objects.filter(user=user).values_list('achievement__key', flat=True))
    if required_super_keys.issubset(unlocked_keys):
        if unlock_achievement(user, 'superperson'):
            unlocked.append('superperson')

    return unlocked