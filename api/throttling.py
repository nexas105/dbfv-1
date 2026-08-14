# Third Party
from rest_framework.throttling import SimpleRateThrottle


class APIKeyRateThrottle(SimpleRateThrottle):
    """Rate-limit per API key (prefix), not per (spoofable) client IP.

    Falls back to the IP when no key is present.
    """

    scope = 'apikey'

    def get_cache_key(self, request, view):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        ident = None
        if auth.startswith('Api-Key '):
            token = auth[len('Api-Key '):].strip()
            ident = token.split('.', 1)[0] or None  # prefix only, never the secret
        if not ident:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}
