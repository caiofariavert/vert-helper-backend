import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.helper.tests.factories import (
    ActionFactory,
    ApplicationFactory,
    EcosystemFactory,
    ServiceFactory,
    SystemFactory,
)

User = get_user_model()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="superuser@helper.test",
        password="test1234",
        name="Super User",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email="user@helper.test",
        password="test1234",
        name="Regular User",
    )


@pytest.fixture
def superuser_client(superuser):
    client = APIClient()
    token = str(RefreshToken.for_user(superuser).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"JWT {token}")
    return client


@pytest.fixture
def regular_client(regular_user):
    client = APIClient()
    token = str(RefreshToken.for_user(regular_user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"JWT {token}")
    return client


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def ecosystem(db):
    return EcosystemFactory()


@pytest.fixture
def system(db, ecosystem):
    s = SystemFactory()
    s.ecosystems.add(ecosystem)
    return s


@pytest.fixture
def application(db, system):
    return ApplicationFactory(system=system)


@pytest.fixture
def service(db, application):
    return ServiceFactory(application=application)


@pytest.fixture
def action(db, application):
    return ActionFactory(application=application)
