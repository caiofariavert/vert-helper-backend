import pytest
from django.contrib.auth import get_user_model
from pytest_factoryboy import register

from apps.user.tests.factories import UserFactory

# Modulo User
register(UserFactory)


@pytest.fixture
def headers():
    """default headers on make request"""
    return {"content_type": "application/json"}


@pytest.fixture
def user():
    """
    Create a user with add_event and view_series permissions
    """
    klass = get_user_model()
    user = klass.objects.create(email="root_tester@root.com.br")
    return user


@pytest.fixture
def specific_user(role):
    """
    Create a user with add_event and view_series permissions
    """
    klass = get_user_model()
    user = klass.objects.create(email="root_tester@root.com.br", role=role)
    return user


@pytest.fixture
def client_permission_user(client, specific_user):
    client.force_login(specific_user)
    return client


@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def client_permission(user, client):
    client.force_login(user)
    return client
