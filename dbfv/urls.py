# Django
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

# Third Party
from django_email_verification import urls as email_urls

# dbfv
from api.contact import api_key_request


urlpatterns = [
    # Django admin (u. a. API-Key-Verwaltung)
    path('admin/', admin.site.urls),

    # REST API
    path('api/v1/', include('api.urls')),
    path('api-key/anfrage', api_key_request, name='api-key-request'),

    # The submission application
    path('core/', include(('core.urls', 'core'), namespace='core')),
    path('', include('submission.urls')),
    path('email-verification/', include(email_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
