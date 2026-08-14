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


class BulkLicensePageSerializer(serializers.Serializer):
    """Paginated envelope returned by the bulk export (documents the response)."""

    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = BulkLicenseSerializer(many=True)


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
        responses=BulkLicensePageSerializer,
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

        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(
                request.query_params.get('page_size', LicensePagination.page_size)
            )
        except ValueError:
            return Response({'detail': 'Ungültige Pagination.'}, status=status.HTTP_400_BAD_REQUEST)
        if page < 1 or page_size < 1:
            return Response({'detail': 'Ungültige Pagination.'}, status=status.HTTP_400_BAD_REQUEST)
        page_size = min(page_size, LicensePagination.max_page_size)
        offset = (page - 1) * page_size

        # Paginate at the DB level: count each type, then materialize only the
        # requested window across the ordered querysets. Avoids loading the full
        # personal-data export into memory.
        total = 0
        results = []
        for slug, (model, label, _has_dob) in types.items():
            queryset = valid_queryset(model, year).order_by('pk')
            count = queryset.count()
            window_start = max(offset, total)
            window_end = min(offset + page_size, total + count)
            if window_start < window_end:
                results += [
                    _bulk_dict(o, slug, label, include_dob)
                    for o in queryset[window_start - total:window_end - total]
                ]
            total += count

        def _page_link(number):
            params = request.query_params.copy()
            params['page'] = number
            return request.build_absolute_uri('?' + params.urlencode())

        return Response({
            'count': total,
            'next': _page_link(page + 1) if offset + page_size < total else None,
            'previous': _page_link(page - 1) if page > 1 else None,
            'results': results,
        })


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


class LicenseLookupResponseSerializer(serializers.Serializer):
    """Envelope actually returned by the lookup endpoint."""

    year = serializers.IntegerField()
    valid = serializers.BooleanField()
    matches = LicenseMatchSerializer(many=True)


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
        responses=LicenseLookupResponseSerializer,
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
