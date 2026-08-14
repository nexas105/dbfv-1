"""Unified read access to license validity across all submission types.

A license == an approved submission for a calendar year.
Valid == submission_status "Bewilligt" AND creation_date.year == <year>.
"""
# Third Party
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

# Django
from django.utils import timezone

# dbfv
from submission.models import (
    SubmissionGym,
    SubmissionInternational,
    SubmissionJudge,
    SubmissionStarter,
)

SUBMISSION_STATUS_BEWILLIGT = SubmissionStarter.SUBMISSION_STATUS_BEWILLIGT

# slug -> (model, label, has date_of_birth). Order = output order.
LICENSE_TYPES = {
    'starter': (SubmissionStarter, 'Starterlizenz', True),
    'international': (SubmissionInternational, 'Internationale Lizenz', True),
    'judge': (SubmissionJudge, 'Kampfrichterlizenz', False),
    'studio': (SubmissionGym, 'Studiolizenz', False),
}


def valid_queryset(model, year):
    return model.objects.filter(submission_status=SUBMISSION_STATUS_BEWILLIGT, creation_date__year=year)


def _year(request):
    raw = request.query_params.get('year')
    if raw:
        return int(raw)  # raises ValueError -> handled by caller
    return timezone.now().year


_YEAR_PARAM = OpenApiParameter(
    'year', int, description='Kalenderjahr der Gültigkeit. Standard: laufendes Jahr.'
)


class BulkLicenseSerializer(serializers.Serializer):
    """Minimal bulk export fields (documents the response)."""

    license_type = serializers.CharField()
    label = serializers.CharField()
    id = serializers.IntegerField()
    name = serializers.CharField()
    year = serializers.IntegerField()
    valid = serializers.BooleanField()
    date_of_birth = serializers.DateField(
        required=False, allow_null=True, help_text='Nur mit ?include=date_of_birth'
    )


class LicensePagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500


def _bulk_dict(obj, slug, label, include_dob):
    # Minimal by default; date_of_birth only when explicitly requested.
    data = {
        'license_type': slug,
        'label': label,
        'id': obj.pk,
        'name': obj.get_name,
        'year': obj.creation_date.year,
        'valid': True,
    }
    if include_dob:
        dob = getattr(obj, 'date_of_birth', None)
        data['date_of_birth'] = dob.isoformat() if dob else None
    return data


class ValidLicensesView(APIView):
    """Alle aktuell gültigen Lizenzen (Massen-Export, nur mit sensitive_access)."""

    # Bulk export of personal data -> require the sensitive scope.
    requires_sensitive = True

    @extend_schema(
        parameters=[
            _YEAR_PARAM,
            OpenApiParameter('type', str, description='Nur ein Typ: ' + ', '.join(LICENSE_TYPES)),
            OpenApiParameter(
                'include', str,
                description='Kommagetrennte Zusatzfelder, aktuell: date_of_birth.',
            ),
        ],
        responses=BulkLicenseSerializer(many=True),
    )
    def get(self, request):
        try:
            year = _year(request)
        except ValueError:
            return Response({'detail': 'Ungültiges Jahr.'}, status=status.HTTP_400_BAD_REQUEST)

        only = request.query_params.get('type')
        if only and only not in LICENSE_TYPES:
            return Response({'detail': 'Unbekannter Typ.'}, status=status.HTTP_400_BAD_REQUEST)
        types = {only: LICENSE_TYPES[only]} if only else LICENSE_TYPES

        include = request.query_params.get('include', '').split(',')
        include_dob = 'date_of_birth' in include

        licenses = []
        for slug, (model, label, _has_dob) in types.items():
            licenses += [
                _bulk_dict(o, slug, label, include_dob) for o in valid_queryset(model, year)
            ]

        paginator = LicensePagination()
        page = paginator.paginate_queryset(licenses, request, view=self)
        return paginator.get_paginated_response(page)


# Which lookup params each type can be filtered by (must exist on the model).
LOOKUP_FIELDS = {
    'starter': {'last_name', 'first_name', 'email', 'date_of_birth'},
    'international': {'last_name', 'first_name', 'email', 'date_of_birth'},
    'judge': {'last_name', 'first_name', 'email'},
    'studio': {'email'},
}


class LicenseMatchSerializer(serializers.Serializer):
    """Data-minimized lookup result: no personal data, just the verdict."""

    license_type = serializers.CharField()
    label = serializers.CharField()
    year = serializers.IntegerField()
    valid = serializers.BooleanField()


class LicenseLookupRequestSerializer(serializers.Serializer):
    """Identifiers accepted in the lookup request body."""

    last_name = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    date_of_birth = serializers.DateField(required=False)
    year = serializers.IntegerField(required=False)

    def validate(self, attrs):
        identifiers = {
            key: value for key, value in attrs.items()
            if key != 'year' and value not in ('', None)
        }
        if len(identifiers) < 2:
            raise serializers.ValidationError(
                'Mindestens zwei Identifikatoren angeben '
                '(last_name, first_name, email, date_of_birth).'
            )
        return attrs


class LicenseLookupView(APIView):
    """
    Datensparsame Gültigkeitsabfrage.

    Sucht gezielt nach einer Person und gibt nur zurück, ob eine gültige Lizenz
    existiert (Typ + Jahr) — keine Personendaten. Zur Vermeidung von
    Enumeration/Scraping müssen **mindestens zwei** Identifikatoren angegeben
    werden.
    """

    # POST is used only to keep personal identifiers out of URLs/access logs.
    # It is semantically read-only and must not require write_allowed.
    read_only_post = True

    @extend_schema(
        request=LicenseLookupRequestSerializer,
        responses=LicenseMatchSerializer(many=True),
    )
    def post(self, request):
        request_serializer = LicenseLookupRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated = request_serializer.validated_data
        year = validated.pop('year', timezone.now().year)
        provided = {
            field: value.isoformat() if hasattr(value, 'isoformat') else value.strip()
            for field, value in validated.items()
        }

        matches = []
        for slug, (model, label, _has_dob) in LICENSE_TYPES.items():
            # Only filters this type actually supports; require >= 2 so a single
            # field can never enumerate a whole type.
            applicable = {f: v for f, v in provided.items() if f in LOOKUP_FIELDS[slug]}
            if len(applicable) < 2:
                continue
            if valid_queryset(model, year).filter(**applicable).exists():
                matches.append(
                    {'license_type': slug, 'label': label, 'year': year, 'valid': True}
                )

        data = LicenseMatchSerializer(matches, many=True).data
        return Response({'year': year, 'valid': bool(data), 'matches': data})
