import pytest

from apps.helper.models import ActionExecutionLog
from apps.helper.tests.factories import (
    SIMPLE_QUESTIONS_SCHEMA,
    ActionFactory,
    ApplicationFactory,
    EcosystemFactory,
    ServiceFactory,
    SystemFactory,
)

# ---------------------------------------------------------------------------
# Health endpoint (sem autenticação)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestHelperHealthView:

    def test_health_returns_ok_without_auth(self, anon_client):
        response = anon_client.get("/api/helper/v1/health/")
        assert response.status_code == 200
        assert response.data["status"] == "ok"


# ---------------------------------------------------------------------------
# WhoAmI endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWhoAmIView:

    def test_unauthenticated_returns_401(self, anon_client):
        response = anon_client.get("/api/helper/v1/me/")
        assert response.status_code == 401

    def test_superuser_returns_is_superuser_true(self, superuser_client, superuser):
        response = superuser_client.get("/api/helper/v1/me/")
        assert response.status_code == 200
        assert response.data["is_superuser"] is True
        assert response.data["email"] == superuser.email

    def test_regular_user_returns_is_superuser_false(self, regular_client):
        response = regular_client.get("/api/helper/v1/me/")
        assert response.status_code == 200
        assert response.data["is_superuser"] is False


# ---------------------------------------------------------------------------
# Permissão IsSuperUser
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIsSuperUserPermission:

    def test_anon_blocked_on_ecosystems(self, anon_client):
        response = anon_client.get("/api/helper/v1/ecosystems/")
        assert response.status_code == 401

    def test_regular_user_blocked_on_ecosystems(self, regular_client):
        response = regular_client.get("/api/helper/v1/ecosystems/")
        assert response.status_code == 403

    def test_superuser_allowed_on_ecosystems(self, superuser_client, db):
        response = superuser_client.get("/api/helper/v1/ecosystems/")
        assert response.status_code == 200

    def test_regular_user_blocked_on_execute(self, regular_client, db):
        app = ApplicationFactory()
        action = ActionFactory(application=app, slug="test-action")
        response = regular_client.post(
            f"/api/helper/v1/actions/{action.slug}/execute/",
            data={"questions": {}},
            format="json",
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Listagem e filtros
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEcosystemListView:

    def test_list_returns_only_active(self, superuser_client):
        eco1 = EcosystemFactory(name="Active Eco")
        eco2 = EcosystemFactory(name="Deleted Eco")
        eco2.soft_delete()

        response = superuser_client.get("/api/helper/v1/ecosystems/")
        slugs = [r["slug"] for r in response.data["results"]]
        assert eco1.slug in slugs
        assert eco2.slug not in slugs

    def test_search_by_name(self, superuser_client):
        EcosystemFactory(name="Alpha Ecosystem")
        EcosystemFactory(name="Beta Ecosystem")

        response = superuser_client.get("/api/helper/v1/ecosystems/?search=Alpha")
        assert response.data["count"] == 1
        assert "alpha" in response.data["results"][0]["slug"]


@pytest.mark.django_db
class TestSystemListView:

    def test_filter_by_ecosystem_slug(self, superuser_client):
        eco_a = EcosystemFactory(name="Eco A")
        eco_b = EcosystemFactory(name="Eco B")
        sys_a = SystemFactory(name="Sys A")
        sys_b = SystemFactory(name="Sys B")
        sys_a.ecosystems.add(eco_a)
        sys_b.ecosystems.add(eco_b)

        response = superuser_client.get(
            f"/api/helper/v1/systems/?ecosystem={eco_a.slug}"
        )
        slugs = [r["slug"] for r in response.data["results"]]
        assert sys_a.slug in slugs
        assert sys_b.slug not in slugs


@pytest.mark.django_db
class TestServiceListView:

    def test_filter_by_application_slug(self, superuser_client):
        app_a = ApplicationFactory(slug="app-a")
        app_b = ApplicationFactory(slug="app-b")
        svc_a = ServiceFactory(application=app_a, name="svc-a")
        svc_b = ServiceFactory(application=app_b, name="svc-b")

        response = superuser_client.get("/api/helper/v1/services/?application=app-a")
        assert response.status_code == 200

        names = [r["name"] for r in response.data["results"]]
        assert svc_a.name in names
        assert svc_b.name not in names

    def test_filter_by_system_slug(self, superuser_client):
        system_a = SystemFactory(slug="sys-a")
        system_b = SystemFactory(slug="sys-b")
        app_a = ApplicationFactory(system=system_a)
        app_b = ApplicationFactory(system=system_b)
        svc_a = ServiceFactory(application=app_a, name="svc-a")
        svc_b = ServiceFactory(application=app_b, name="svc-b")

        response = superuser_client.get("/api/helper/v1/services/?system=sys-a")
        assert response.status_code == 200

        names = [r["name"] for r in response.data["results"]]
        assert svc_a.name in names
        assert svc_b.name not in names


@pytest.mark.django_db
class TestApplicationListStatus:

    def test_application_status_failed_when_any_service_failed(self, superuser_client):
        app = ApplicationFactory(name="App Failed", slug="app-failed")
        ServiceFactory(application=app, status="OK")
        ServiceFactory(application=app, status="FAILED")

        response = superuser_client.get(
            "/api/helper/v1/applications/?search=App Failed"
        )
        assert response.status_code == 200
        result = next(r for r in response.data["results"] if r["slug"] == "app-failed")
        assert result["status"] == "FAILED"

    def test_application_status_ok_when_all_services_ok(self, superuser_client):
        app = ApplicationFactory(name="App Ok", slug="app-ok")
        ServiceFactory(application=app, status="OK")
        ServiceFactory(application=app, status="OK")

        response = superuser_client.get("/api/helper/v1/applications/?search=App Ok")
        assert response.status_code == 200
        result = next(r for r in response.data["results"] if r["slug"] == "app-ok")
        assert result["status"] == "OK"


@pytest.mark.django_db
class TestActionListView:

    def test_is_recommended_true_when_service_failed(self, superuser_client):
        app = ApplicationFactory()
        svc = ServiceFactory(application=app, status="FAILED")
        action = ActionFactory(application=app)
        action.services.add(svc)

        response = superuser_client.get("/api/helper/v1/actions/")
        result = next(r for r in response.data["results"] if r["slug"] == action.slug)
        assert result["is_recommended"] is True

    def test_is_recommended_false_when_service_ok(self, superuser_client):
        app = ApplicationFactory()
        svc = ServiceFactory(application=app, status="OK")
        action = ActionFactory(application=app)
        action.services.add(svc)

        response = superuser_client.get("/api/helper/v1/actions/")
        result = next(r for r in response.data["results"] if r["slug"] == action.slug)
        assert result["is_recommended"] is False

    def test_filter_by_service_name(self, superuser_client):
        app = ApplicationFactory()
        svc = ServiceFactory(application=app, name="kafka")
        action_with = ActionFactory(application=app, slug="with-kafka")
        ActionFactory(application=app, slug="without-kafka")
        action_with.services.add(svc)

        response = superuser_client.get("/api/helper/v1/actions/?service=kafka")
        slugs = [r["slug"] for r in response.data["results"]]
        assert "with-kafka" in slugs
        assert "without-kafka" not in slugs


@pytest.mark.django_db
class TestActionDetailView:

    def test_detail_includes_questions(self, superuser_client):
        app = ApplicationFactory()
        action = ActionFactory(
            application=app, questions_schema=SIMPLE_QUESTIONS_SCHEMA
        )

        response = superuser_client.get(f"/api/helper/v1/actions/{action.slug}/")
        assert response.status_code == 200
        assert len(response.data["questions"]) == 3
        assert response.data["questions"][0]["id"] == "q1"


# ---------------------------------------------------------------------------
# Execute action
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestActionExecuteView:

    def test_invalid_questions_returns_400(self, superuser_client):
        app = ApplicationFactory()
        action = ActionFactory(
            application=app, questions_schema=SIMPLE_QUESTIONS_SCHEMA
        )

        response = superuser_client.post(
            f"/api/helper/v1/actions/{action.slug}/execute/",
            data={"questions": {}},
            format="json",
        )
        assert response.status_code == 400
        assert "questions" in response.data

    def test_valid_questions_calls_external_and_logs(
        self, superuser_client, superuser, requests_mock
    ):
        app = ApplicationFactory(base_url="http://external.example.com")
        action = ActionFactory(
            application=app, questions_schema=SIMPLE_QUESTIONS_SCHEMA
        )

        requests_mock.post(
            "http://external.example.com/api/helper/v1/actions/execute/",
            json={"status": "success", "message": "Executado com sucesso"},
        )
        # URL real que o serviço vai chamar
        requests_mock.post(
            f"http://external.example.com/api/helper/v1/actions/{action.slug}/execute/",
            json={"status": "success", "message": "Executado com sucesso"},
        )

        response = superuser_client.post(
            f"/api/helper/v1/actions/{action.slug}/execute/",
            data={"questions": {"q1": "CSV", "q2": "Arquivo"}},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "success"

        log = ActionExecutionLog.objects.get(action=action)
        assert log.result_status == ActionExecutionLog.RESULT_SUCCESS
        assert log.mapped_kwargs == {"file_type": "CSV", "csv_source": "Arquivo"}
        assert log.executed_by == superuser

    def test_external_error_returns_422_and_logs(self, superuser_client, requests_mock):
        app = ApplicationFactory(base_url="http://external.example.com")
        action = ActionFactory(
            application=app, questions_schema=SIMPLE_QUESTIONS_SCHEMA
        )

        requests_mock.post(
            f"http://external.example.com/api/helper/v1/actions/{action.slug}/execute/",
            json={"status": "error", "message": "Falha", "details": "DB down"},
        )

        response = superuser_client.post(
            f"/api/helper/v1/actions/{action.slug}/execute/",
            data={"questions": {"q1": "JSON", "q3": "wf-1"}},
            format="json",
        )

        assert response.status_code == 422
        assert response.data["status"] == "error"
        # details NÃO deve aparecer na resposta ao frontend
        assert "details" not in response.data

        log = ActionExecutionLog.objects.get(action=action)
        assert log.result_details == "DB down"
