# Third Party
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

# Django
from django.urls import path

# dbfv
from api.licenses import LicenseLookupView, ValidLicensesView
from api.views import VIEWSETS

router = DefaultRouter()
for slug, viewset in VIEWSETS.items():
    router.register(slug, viewset, basename=slug)

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('licenses/valid/', ValidLicensesView.as_view(), name='licenses-valid'),
    path('licenses/lookup/', LicenseLookupView.as_view(), name='licenses-lookup'),
    *router.urls,
]
