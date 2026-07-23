import pytest

from apps.helper.integrations.incident_manager import handle_service_status_change
from apps.helper.models import Incident, Service
from apps.helper.tests.factories import IncidentFactory, ServiceFactory


@pytest.mark.django_db
class TestHandleServiceStatusChange:

    def test_opens_incident_on_ok_to_failed(self, db):
        svc = ServiceFactory(status=Service.STATUS_OK)

        handle_service_status_change(svc, Service.STATUS_OK, Service.STATUS_FAILED)

        assert Incident.objects.filter(service=svc, is_active=True).exists()

    def test_no_duplicate_incident_when_already_active(self, db):
        svc = ServiceFactory(status=Service.STATUS_FAILED)
        IncidentFactory(service=svc, is_active=True)

        handle_service_status_change(svc, Service.STATUS_FAILED, Service.STATUS_FAILED)

        assert Incident.objects.filter(service=svc, is_active=True).count() == 1

    def test_closes_incident_on_failed_to_ok(self, db):
        svc = ServiceFactory(status=Service.STATUS_FAILED)
        incident = IncidentFactory(service=svc, is_active=True)

        handle_service_status_change(svc, Service.STATUS_FAILED, Service.STATUS_OK)

        incident.refresh_from_db()
        assert incident.is_active is False
        assert incident.recovered_at is not None
        assert incident.current_status == Service.STATUS_OK

    def test_unknown_status_does_not_open_incident(self, db):
        svc = ServiceFactory(status=Service.STATUS_OK)

        handle_service_status_change(svc, Service.STATUS_OK, Service.STATUS_UNKNOWN)

        assert not Incident.objects.filter(service=svc).exists()

    def test_no_action_when_status_unchanged(self, db):
        svc = ServiceFactory(status=Service.STATUS_OK)

        handle_service_status_change(svc, Service.STATUS_OK, Service.STATUS_OK)

        assert not Incident.objects.filter(service=svc).exists()

    def test_previous_status_recorded_in_incident(self, db):
        svc = ServiceFactory(status=Service.STATUS_UNKNOWN)

        handle_service_status_change(svc, Service.STATUS_UNKNOWN, Service.STATUS_FAILED)

        incident = Incident.objects.get(service=svc)
        assert incident.previous_status == Service.STATUS_UNKNOWN
