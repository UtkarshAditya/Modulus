import factory

from .models import DEFAULT_THRESHOLDS, Policy


class PolicyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Policy

    version = factory.Sequence(lambda n: n + 1)
    is_active = False
    thresholds = factory.LazyFunction(lambda: dict(DEFAULT_THRESHOLDS))
    rule_config = factory.LazyFunction(dict)
