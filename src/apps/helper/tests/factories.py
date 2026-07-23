import factory
from django.utils.text import slugify

from apps.helper.models import (
    Action,
    Application,
    Ecosystem,
    Incident,
    Service,
    System,
)


class EcosystemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ecosystem

    name = factory.Sequence(lambda n: f"Ecosystem {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))


class SystemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = System

    name = factory.Sequence(lambda n: f"System {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))


class ApplicationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Application

    name = factory.Sequence(lambda n: f"Application {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    base_url = "http://app.example.com"
    environment = Application.ENVIRONMENT_STG
    auth_type = Application.AUTH_NONE
    system = factory.SubFactory(SystemFactory)


class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Service

    name = factory.Sequence(lambda n: f"service-{n}")
    status = Service.STATUS_OK
    application = factory.SubFactory(ApplicationFactory)


class ActionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Action

    slug = factory.Sequence(lambda n: f"action-{n}")
    name = factory.Sequence(lambda n: f"Action {n}")
    questions_schema = []
    source_version = 1
    application = factory.SubFactory(ApplicationFactory)


class IncidentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Incident

    service = factory.SubFactory(ServiceFactory)
    previous_status = Service.STATUS_OK
    current_status = Service.STATUS_FAILED
    is_active = True


SIMPLE_QUESTIONS_SCHEMA = [
    {
        "id": "q1",
        "label": "Tipo de arquivo",
        "type": "radio",
        "options": ["CSV", "JSON"],
        "is_required": True,
        "parent_question": None,
        "parent_value": None,
        "action_kwarg": "file_type",
    },
    {
        "id": "q2",
        "label": "Fonte do CSV",
        "type": "radio",
        "options": ["Arquivo", "URL"],
        "is_required": True,
        "parent_question": "q1",
        "parent_value": "CSV",
        "action_kwarg": "csv_source",
    },
    {
        "id": "q3",
        "label": "ID do Workflow",
        "type": "text",
        "options": None,
        "is_required": True,
        "parent_question": "q1",
        "parent_value": "JSON",
        "action_kwarg": "workflow_id",
    },
]
