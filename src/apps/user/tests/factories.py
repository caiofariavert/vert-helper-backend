import factory
import factory.fuzzy
import pytz
from django.conf import settings

from apps.user.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda a: "teste@teste.com".lower())
    name = factory.fuzzy.FuzzyText(length=80)
    date_joined = factory.Faker("date_time", tzinfo=pytz.timezone(settings.TIME_ZONE))
    is_staff = factory.fuzzy.FuzzyChoice([True, False])
    is_active = factory.fuzzy.FuzzyChoice([True, False])
