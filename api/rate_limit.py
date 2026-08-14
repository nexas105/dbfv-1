"""Cache-backed fixed-window limits for pre-authentication endpoints."""

# Standard Library
import hashlib
import time

# Django
from django.core.cache import cache


_PERIODS = {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}


def parse_rate(rate):
    """Parse DRF-style rates such as ``120/minute``."""
    amount, period = rate.split('/', 1)
    return int(amount), _PERIODS[period.rstrip('s')]


def check_rate_limit(scope, identifier, rate):
    """Return ``(allowed, retry_after)`` for a cache-backed fixed window."""
    limit, seconds = parse_rate(rate)
    now = int(time.time())
    window = now // seconds
    digest = hashlib.sha256(identifier.encode('utf-8')).hexdigest()
    key = f'dbfv-rate:{scope}:{digest}:{window}'

    if cache.add(key, 1, timeout=seconds + 1):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=seconds + 1)
            count = 1

    retry_after = seconds - (now % seconds)
    return count <= limit, retry_after
