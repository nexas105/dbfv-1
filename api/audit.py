"""Audit logging for API usage.

Never logs the API-key secret, the request body, or the query string (which can
carry search data). Only the key prefix, client IP, method, path and status.
"""
# Standard Library
import logging

logger = logging.getLogger('dbfv.audit')


def key_prefix(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Api-Key '):
        token = auth[len('Api-Key '):].strip()
        return token.split('.', 1)[0] or '-'  # prefix only, never the secret
    return '-'


def log_api_access(request, status_code, client):
    level = logging.WARNING if status_code in (401, 403, 429) else logging.INFO
    logger.log(
        level,
        'api access key=%s ip=%s method=%s path=%s status=%s',
        key_prefix(request), client or '-', request.method, request.path, status_code,
    )


def log_key_revoked(prefix, actor):
    logger.warning('api key revoked key=%s by=%s', prefix or '-', actor or '-')
