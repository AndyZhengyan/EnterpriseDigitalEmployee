"""E2E: Config Center — full lifecycle: create, update, publish, rollback, audit."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def config_center_seeded():
    """Ensure config center seed functions are called before each test."""
    from apps.config_center.store import seed_defaults

    seed_defaults()


@pytest.fixture
def config_center_client():
    from apps.config_center.main import app

    return TestClient(app)


class TestConfigCenterHealth:
    def test_health_returns_counts(self, config_center_client):
        response = config_center_client.get("/config-center/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "namespace_count" in data
        assert "item_count" in data


class TestConfigCenterNamespaces:
    def test_list_namespaces_returns_seed_defaults(self, config_center_client):
        response = config_center_client.get("/config-center/namespaces")
        assert response.status_code == 200
        namespaces = response.json()
        namespace_names = {ns["namespace"] for ns in namespaces}
        assert "feature_flags" in namespace_names
        assert "model_routing" in namespace_names
        assert "alerting" in namespace_names

    def test_create_namespace(self, config_center_client):
        response = config_center_client.post(
            "/config-center/namespaces",
            params={"namespace": "my-namespace", "description": "Test namespace"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["namespace"] == "my-namespace"
        assert data["description"] == "Test namespace"


class TestConfigCenterLifecycle:
    def test_create_update_publish_config(self, config_center_client):
        # Create a new config in draft
        response = config_center_client.post(
            "/config-center/configs",
            json={
                "namespace": "feature_flags",
                "key": "test_flag",
                "value": False,
                "description": "Test feature flag",
                "created_by": "e2e-test",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "test_flag"
        assert data["value"] is False
        assert data["status"] == "draft"
        assert data["version"] == 1

        # Update the value (new draft version)
        response = config_center_client.put(
            "/config-center/configs/feature_flags/test_flag",
            json={"value": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is True
        assert data["version"] == 2

        # Publish
        response = config_center_client.post(
            "/config-center/configs/feature_flags/test_flag/publish",
            params={"changed_by": "e2e-test", "comment": "Going live"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None

    def test_config_not_found_returns_404(self, config_center_client):
        response = config_center_client.get("/config-center/configs/nonexistent_namespace/no-such-key")
        assert response.status_code == 404

    def test_duplicate_config_returns_409(self, config_center_client):
        # Create
        config_center_client.post(
            "/config-center/configs",
            json={
                "namespace": "model_routing",
                "key": "dup_test",
                "value": "v1",
                "created_by": "e2e-test",
            },
        )
        # Try to create again
        response = config_center_client.post(
            "/config-center/configs",
            json={
                "namespace": "model_routing",
                "key": "dup_test",
                "value": "v2",
                "created_by": "e2e-test",
            },
        )
        assert response.status_code == 409

    def test_deprecate_config(self, config_center_client):
        # Create and publish first
        config_center_client.post(
            "/config-center/configs",
            json={
                "namespace": "alerting",
                "key": "old_threshold",
                "value": 0.1,
                "created_by": "e2e-test",
            },
        )
        config_center_client.post(
            "/config-center/configs/alerting/old_threshold/publish",
            params={"changed_by": "e2e-test"},
        )
        # Deprecate
        response = config_center_client.delete("/config-center/configs/alerting/old_threshold")
        assert response.status_code == 200
        assert response.json()["deprecated"] is True


class TestConfigCenterVersionHistory:
    def test_version_history_records_changes(self, config_center_client):
        # Create → update → publish
        config_center_client.post(
            "/config-center/configs",
            json={
                "namespace": "model_routing",
                "key": "version_test",
                "value": "v1",
                "created_by": "e2e-test",
            },
        )
        config_center_client.put(
            "/config-center/configs/model_routing/version_test",
            json={"value": "v2"},
        )
        config_center_client.post(
            "/config-center/configs/model_routing/version_test/publish",
            params={"changed_by": "e2e-test"},
        )

        # Get version history
        response = config_center_client.get(
            "/config-center/configs/model_routing/version_test/versions",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "version_test"
        assert data["total"] == 3  # created, updated, published

    def test_rollback_restores_previous_value(self, config_center_client):
        # Create v1 → update v2 → publish → rollback to v1
        config_center_client.post(
            "/config-center/configs",
            json={
                "namespace": "feature_flags",
                "key": "rollback_test",
                "value": "original",
                "created_by": "e2e-test",
            },
        )
        config_center_client.post(
            "/config-center/configs/feature_flags/rollback_test/publish",
            params={"changed_by": "e2e-test"},
        )
        config_center_client.put(
            "/config-center/configs/feature_flags/rollback_test",
            json={"value": "changed"},
        )

        # Get versions to find v1
        response = config_center_client.get(
            "/config-center/configs/feature_flags/rollback_test/versions",
        )
        versions = response.json()["versions"]
        v1 = next(v for v in versions if v["value"] == "original")

        # Rollback
        response = config_center_client.post(
            "/config-center/configs/feature_flags/rollback_test/rollback",
            params={
                "target_version": v1["version"],
                "changed_by": "e2e-test",
                "comment": "Rollback to original",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "original"


class TestConfigCenterAuditTrail:
    def test_audit_log_records_changes(self, config_center_client):
        # Create a config
        config_center_client.post(
            "/config-center/configs",
            json={
                "namespace": "alerting",
                "key": "audit_test",
                "value": 0.5,
                "created_by": "e2e-test",
            },
        )
        config_center_client.post(
            "/config-center/configs/alerting/audit_test/publish",
            params={"changed_by": "e2e-test"},
        )

        # Check audit log
        response = config_center_client.get("/config-center/audit")
        assert response.status_code == 200
        data = response.json()
        assert "changes" in data
        assert "total" in data
        assert data["total"] >= 2  # created + published

    def test_audit_filtered_by_namespace(self, config_center_client):
        response = config_center_client.get(
            "/config-center/audit",
            params={"namespace": "feature_flags"},
        )
        assert response.status_code == 200
        changes = response.json()["changes"]
        for change in changes:
            assert change["namespace"] == "feature_flags"


class TestConfigCenterSubscribers:
    def test_register_and_list_subscriber(self, config_center_client):
        response = config_center_client.post(
            "/config-center/subscribers",
            json={
                "service_id": "runtime",
                "name": "Runtime Service",
                "url": "http://runtime:8001/config-hook",
                "namespaces": ["feature_flags", "model_routing"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["service_id"] == "runtime"
        assert data["active"] is True

        # List subscribers
        response = config_center_client.get("/config-center/subscribers")
        assert response.status_code == 200
        subscribers = response.json()
        assert any(s["service_id"] == "runtime" for s in subscribers)

    def test_unregister_subscriber(self, config_center_client):
        # Register
        config_center_client.post(
            "/config-center/subscribers",
            json={
                "service_id": "temp-service",
                "name": "Temp",
                "url": "http://temp:9000/hook",
            },
        )
        # Unregister
        response = config_center_client.delete("/config-center/subscribers/temp-service")
        assert response.status_code == 200
        assert response.json()["unregistered"] is True

        # Verify gone
        response = config_center_client.delete("/config-center/subscribers/temp-service")
        assert response.status_code == 404
