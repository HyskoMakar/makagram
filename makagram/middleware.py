from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin


class ActiveUserMiddleware(MiddlewareMixin):
    """Mark authenticated users as online in the cache.

    Sets cache key `online_user_<id>` with a short timeout on each request.
    """

    TIMEOUT = 12
    
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            cache.set(f'online_user_{user.id}', True, self.TIMEOUT)
