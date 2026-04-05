"""E2E: Health endpoint validation for all services."""

import pytest


def _import_app(module_path: str):
    """Import FastAPI app from module path string."""
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, "app", None)


@pytest.mark.parametrize(
    "app_module,health_path,service_name",
    [
        ("apps.gateway.main", "/gateway/health", "Gateway"),
        ("apps.runtime.main", "/runtime/health", "Runtime"),
        ("apps.model_hub.main", "/model-hub/health", "ModelHub"),
        ("apps.connector_hub.main", "/connector-hub/health", "ConnectorHub"),
        ("apps.skill_hub.main", "/skill-hub/health", "SkillHub"),
        ("apps.knowledge_hub.main", "/knowledge-hub/health", "KnowledgeHub"),
        ("apps.ops_center.main", "/ops/health", "OpsCenter"),
        ("apps.governance.main", "/governance/health", "Governance"),
        ("apps.config_center.main", "/config-center/health", "ConfigCenter"),
    ],
)
def test_service_health_endpoint(app_module, health_path, service_name):
    """Each service must expose a health check endpoint."""
    app = _import_app(app_module)
    if app is None:
        pytest.skip(f"{service_name} app not found (may not be implemented yet)")

    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get(health_path)
    assert response.status_code == 200, f"{service_name} health check failed: {response.text}"
    data = response.json()
    assert data["status"] == "healthy", f"{service_name} reports unhealthy"
    assert "version" in data, f"{service_name} health response missing 'version'"
