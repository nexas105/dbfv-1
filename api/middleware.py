"""Pre-authentication protection for the REST API."""

# Django
from django.conf import settings
from django.http import JsonResponse

# dbfv
from api.audit import log_api_access
from api.client_ip import client_ip
from api.rate_limit import check_rate_limit


class ApiAuditMiddleware:
    """Audit every API response (usage, 403, 429) without logging secrets/search data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/v1/'):
            log_api_access(request, response.status_code, client_ip(request))
        return response


class ApiPreAuthRateLimitMiddleware:
    """Limit API traffic by IP before DRF performs API-key verification."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/v1/'):
            rate = getattr(settings, 'API_PREAUTH_RATE_LIMIT', '120/minute')
            allowed, retry_after = check_rate_limit(
                'api-preauth', client_ip(request) or 'unknown', rate
            )
            if not allowed:
                response = JsonResponse(
                    {'detail': 'Zu viele Anfragen. Bitte später erneut versuchen.'},
                    status=429,
                )
                response['Retry-After'] = str(retry_after)
                return response
        return self.get_response(request)
