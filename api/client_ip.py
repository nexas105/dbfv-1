"""Resolve client addresses used by API security controls."""

# Django
from django.conf import settings


def client_ip(request):
    """Return a client IP without trusting arbitrary forwarding headers."""
    proxies = getattr(settings, 'API_TRUSTED_PROXY_COUNT', 0)
    if proxies > 0:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        parts = [part.strip() for part in forwarded.split(',') if part.strip()]
        if len(parts) >= proxies:
            return parts[-proxies]
        return ''
    return request.META.get('REMOTE_ADDR', '')
