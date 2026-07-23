import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.helper.integrations.health_sync import sync_health_for_application
from apps.helper.integrations.action_sync import sync_actions_for_application
from apps.helper.models import (
    Action,
    HealthCheckLog,
    Incident,
    Service,
    SyncLog,
)
from apps.helper.tasks import cleanup_health_check_logs
from apps.helper.tests.factories import ApplicationFactory, ServiceFactory


# ---------------------------------------------------------------------------
# Health sync
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncHealthForApplication:

    def _mock_ok(self, requests_mock, app):
        requests_mock.get(f"{app.base_url}/api/helper/v1/app-health/", json={"status": "stable"})
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/healthcare/",
            json={
                "S3": {"status": "OK", "last_updated": "2024-01-01T00:00:00Z"},
                "KAFKA": {"status": "FAILED", "message": "timeout", "last_updated": None},
            },
        )

    def test_creates_new_services(self, db, requests_mock):
        app = ApplicationFactory()
        self._mock_ok(requests_mock, app)

        sync_health_for_application(app)

        assert Service.objects.filter(application=app).count() == 2
        assert Service.objects.get(application=app, name="S3").status == "OK"
        assert Service.objects.get(application=app, name="KAFKA").status == "FAILED"

    def test_creates_health_check_logs(self, db, requests_mock):
        app = ApplicationFactory()
        self._mock_ok(requests_mock, app)

        sync_health_for_application(app)

        assert HealthCheckLog.objects.filter(application=app).count() == 2

    def test_creates_sync_log_on_success(self, db, requests_mock):
        app = ApplicationFactory()
        self._mock_ok(requests_mock, app)

        sync_health_for_application(app)

        log = SyncLog.objects.get(application=app, sync_type=SyncLog.SYNC_SERVICES)
        assert log.status == SyncLog.STATUS_SUCCESS

    def test_inactivates_services_absent_from_origin(self, db, requests_mock):
        app = ApplicationFactory()
        old_svc = ServiceFactory(application=app, name="REDIS")
        requests_mock.get(f"{app.base_url}/api/helper/v1/app-health/", json={"status": "stable"})
        requests_mock.get(f"{app.base_url}/api/helper/v1/healthcare/", json={})

        sync_health_for_application(app)

        old_svc.refresh_from_db()
        assert old_svc.deleted_at is not None

    def test_app_health_failed_marks_all_services_failed(self, db, requests_mock):
        app = ApplicationFactory()
        svc = ServiceFactory(application=app, name="DB", status=Service.STATUS_OK)
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/app-health/",
            json={"status": "failed", "message": "App down"},
        )

        sync_health_for_application(app)

        svc.refresh_from_db()
        assert svc.status == Service.STATUS_FAILED

    def test_opens_incident_on_status_change_to_failed(self, db, requests_mock):
        app = ApplicationFactory()
        ServiceFactory(application=app, name="DB", status=Service.STATUS_OK)
        requests_mock.get(f"{app.base_url}/api/helper/v1/app-health/", json={"status": "stable"})
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/healthcare/",
            json={"DB": {"status": "FAILED", "message": "conn error", "last_updated": None}},
        )

        sync_health_for_application(app)

        assert Incident.objects.filter(service__name="DB", is_active=True).exists()


# ---------------------------------------------------------------------------
# Action sync
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSyncActionsForApplication:

    def test_creates_new_actions(self, db, requests_mock):
        app = ApplicationFactory()
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/actions/",
            json={"count": 1, "next": None, "results": [
                {"slug": "my-action", "name": "My Action", "description": "", "services": [], "status": "active"},
            ]},
        )
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/actions/my-action/",
            json={"slug": "my-action", "name": "My Action", "description": "", "services": [], "questions": []},
        )

        sync_actions_for_application(app)

        assert Action.objects.filter(application=app, slug="my-action").exists()

    def test_increments_version_on_name_change(self, db, requests_mock):
        app = ApplicationFactory()
        action = Action.objects.create(
            application=app, slug="my-action", name="Old Name", questions_schema=[], source_version=1
        )
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/actions/",
            json={"count": 1, "next": None, "results": [
                {"slug": "my-action", "name": "New Name", "description": "", "services": [], "status": "active"},
            ]},
        )
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/actions/my-action/",
            json={"slug": "my-action", "name": "New Name", "description": "", "services": [], "questions": []},
        )

        sync_actions_for_application(app)

        action.refresh_from_db()
        assert action.name == "New Name"
        assert action.source_version == 2

    def test_inactivates_absent_actions(self, db, requests_mock):
        app = ApplicationFactory()
        action = Action.objects.create(
            application=app, slug="old-action", name="Old", questions_schema=[], source_version=1
        )
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/actions/",
            json={"count": 0, "next": None, "results": []},
        )

        sync_actions_for_application(app)

        action.refresh_from_db()
        assert action.deleted_at is not None

    def test_creates_sync_log(self, db, requests_mock):
        app = ApplicationFactory()
        requests_mock.get(
            f"{app.base_url}/api/helper/v1/actions/",
            json={"count": 0, "next": None, "results": []},
        )

        sync_actions_for_application(app)

        assert SyncLog.objects.filter(application=app, sync_type=SyncLog.SYNC_ACTIONS).exists()


# ---------------------------------------------------------------------------
# Cleanup task
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCleanupHealthCheckLogs:

    def test_removes_logs_older_than_90_days(self, db):
        app = ApplicationFactory()

        with freeze_time("2024-01-01"):
            from apps.helper.models import HealthCheckLog
            old = HealthCheckLog.objects.create(
                application=app, service_name="DB", status="OK", raw_payload={}
            )

        with freeze_time("2024-04-05"):  # 95 dias depois
            cleanup_health_check_logs()

        assert not HealthCheckLog.objects.filter(pk=old.pk).exists()

    def test_keeps_logs_within_90_days(self, db):
        app = ApplicationFactory()

        with freeze_time("2024-01-01"):
            from apps.helper.models import HealthCheckLog
            recent = HealthCheckLog.objects.create(
                application=app, service_name="DB", status="OK", raw_payload={}
            )

        with freeze_time("2024-03-01"):  # 59 dias depois
            cleanup_health_check_logs()

        assert HealthCheckLog.objects.filter(pk=recent.pk).exists()
