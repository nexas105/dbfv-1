# Third Party
from rest_framework import serializers, viewsets

# dbfv
from core.models import EmailCron
from submission.models import (
    BankAccount,
    Country,
    Gym,
    ManagerEmail,
    State,
    SubmissionGym,
    SubmissionInternational,
    SubmissionJudge,
    SubmissionStarter,
    UserProfile,
)

# All models exposed via CRUD. Access per key is configurable: read for any
# valid key, write only when the key has write_allowed set.
# ponytail: submission write may need fields the model marks editable=False
# (e.g. user). Primary use is read; extend serializers if write is needed.
API_MODELS = [
    Gym,
    State,
    Country,
    BankAccount,
    ManagerEmail,
    EmailCron,
    UserProfile,
    SubmissionStarter,
    SubmissionInternational,
    SubmissionGym,
    SubmissionJudge,
]


# Field types django-filter can filter on with an exact lookup.
_FILTERABLE = {
    'CharField', 'TextField', 'EmailField', 'SlugField', 'BooleanField',
    'IntegerField', 'BigIntegerField', 'SmallIntegerField', 'PositiveIntegerField',
    'PositiveSmallIntegerField', 'DateField', 'DateTimeField', 'ForeignKey',
}
_SEARCHABLE = {'CharField', 'TextField', 'EmailField', 'SlugField'}


def _serializer_for(model):
    meta = type('Meta', (), {'model': model, 'fields': '__all__'})
    return type(f'{model.__name__}Serializer', (serializers.ModelSerializer,), {'Meta': meta})


def _viewset_for(model):
    fields = model._meta.fields  # concrete local fields (FKs by name, no m2m/reverse)
    return type(
        f'{model.__name__}ViewSet',
        (viewsets.ModelViewSet,),
        {
            'queryset': model._default_manager.all().order_by('pk'),
            'serializer_class': _serializer_for(model),
            # ?field=value exact filter, ?search=, ?ordering=
            'filterset_fields': [f.name for f in fields if f.get_internal_type() in _FILTERABLE],
            'search_fields': [f.name for f in fields if f.get_internal_type() in _SEARCHABLE],
            'ordering_fields': '__all__',
        },
    )


# {url slug: viewset} — consumed by api/urls.py router.
VIEWSETS = {model.__name__.lower(): _viewset_for(model) for model in API_MODELS}
