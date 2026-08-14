# Third Party
from rest_framework_api_key.admin import APIKeyModelAdmin

# Django
from django.contrib import admin

# dbfv
from api.audit import log_key_revoked
from api.models import ScopedAPIKey


@admin.register(ScopedAPIKey)
class ScopedAPIKeyAdmin(APIKeyModelAdmin):
    list_display = [
        *APIKeyModelAdmin.list_display, 'write_allowed', 'sensitive_access', 'allowed_ips',
    ]
    list_filter = [*APIKeyModelAdmin.list_filter, 'write_allowed', 'sensitive_access']

    def save_model(self, request, obj, form, change):
        if 'revoked' in form.changed_data and obj.revoked:
            log_key_revoked(obj.prefix, request.user.get_username())
        super().save_model(request, obj, form, change)
