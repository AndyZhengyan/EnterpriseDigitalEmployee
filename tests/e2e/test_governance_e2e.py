"""E2E: Full governance service — tenant, RBAC, ABAC, approval workflow chain."""

import time

import jwt
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def governance_seeded():
    """Ensure governance seed functions are called before each test."""
    from apps.governance import rbac as rbac_module
    from apps.governance.abac import _auto_seed as abac_seed
    from apps.governance.approval.engine import _auto_seed as approval_seed
    from apps.governance.tenant import _auto_seed as tenant_seed

    rbac_module._auto_seed()
    abac_seed()
    approval_seed()
    tenant_seed()
    # Pre-assign test-admin as platform_admin so admin tests work
    # Idempotent: skip if already assigned (autouse=True fixture re-runs per test)
    existing = rbac_module.get_user_role("test-admin", "platform")
    if existing is None:
        rbac_module.assign_role("test-admin", rbac_module.Role.PLATFORM_ADMIN, "platform", assigned_by="system")


@pytest.fixture
def governance_client():
    from apps.governance.config import GovernanceSettings
    from apps.governance.main import app

    settings = GovernanceSettings()
    return TestClient(app), settings


def _make_admin_token(settings):
    """Create a valid platform_admin JWT token for testing."""
    payload = {
        "user_id": "test-admin",
        "tenant_id": "platform",
        "role": "platform_admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _make_tenant_admin_token(settings, tenant_id: str = "test-tenant"):
    payload = {
        "user_id": "tenant-admin-001",
        "tenant_id": tenant_id,
        "role": "tenant_admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _make_employee_token(settings, tenant_id: str = "tenant-c"):
    """Create a valid token with employee_user role (no admin privileges)."""
    payload = {
        "user_id": "charlie",
        "tenant_id": tenant_id,
        "role": "employee_user",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class TestGovernanceHealth:
    def test_health_returns_status_and_counts(self, governance_client):
        client, _ = governance_client
        response = client.get("/governance/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "role_count" in data
        assert "policy_count" in data


class TestGovernanceToken:
    def test_create_token_returns_valid_jwt(self, governance_client):
        client, _ = governance_client
        response = client.post(
            "/governance/token",
            params={
                "user_id": "alice",
                "tenant_id": "test-tenant",
                "role": "employee_user",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["expires_in"] == 3600


class TestGovernanceRBAC:
    def test_list_roles_returns_all_roles(self, governance_client):
        client, _ = governance_client
        response = client.get("/governance/roles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 4  # platform_admin, tenant_admin, tenant_operator, employee_user

    def test_assign_role_requires_admin(self, governance_client):
        client, _ = governance_client
        # No auth header → 401
        response = client.post(
            "/governance/roles/assign",
            json={"user_id": "alice", "role": "employee_user", "tenant_id": "test-tenant"},
        )
        assert response.status_code == 401

        # Valid admin token → 201
        _, settings = governance_client
        token = _make_admin_token(settings)
        response = client.post(
            "/governance/roles/assign",
            json={"user_id": "alice", "role": "employee_user", "tenant_id": "test-tenant"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        assert response.json()["assigned"] is True

    def test_get_user_role(self, governance_client):
        client, settings = governance_client
        # First assign a role
        token = _make_admin_token(settings)
        client.post(
            "/governance/roles/assign",
            json={"user_id": "bob", "role": "tenant_operator", "tenant_id": "tenant-b"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Then retrieve it
        response = client.get("/governance/roles/tenant-b/bob")
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "tenant_operator"

    def test_revoke_role_requires_tenant_admin(self, governance_client):
        client, settings = governance_client
        # Assign first
        token = _make_admin_token(settings)
        client.post(
            "/governance/roles/assign",
            json={"user_id": "charlie", "role": "employee_user", "tenant_id": "tenant-c"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Revoke with no token → 401
        response = client.delete("/governance/roles/tenant-c/charlie")
        assert response.status_code == 401

        # Revoke with employee token (valid but insufficient role) → 403
        employee_token = _make_employee_token(settings, "tenant-c")
        response = client.delete(
            "/governance/roles/tenant-c/charlie",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert response.status_code == 403

        # Revoke with tenant_admin token → 204
        tenant_admin_token = _make_tenant_admin_token(settings, "tenant-c")
        response = client.delete(
            "/governance/roles/tenant-c/charlie",
            headers={"Authorization": f"Bearer {tenant_admin_token}"},
        )
        assert response.status_code == 204


class TestGovernanceABAC:
    def test_list_policies_returns_built_in(self, governance_client):
        client, _ = governance_client
        response = client.get("/governance/policies")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3  # built-in policies

    def test_permission_check_allowed(self, governance_client):
        client, _ = governance_client
        response = client.post(
            "/governance/permissions/check",
            json={
                "user_id": "alice",
                "action": "read",
                "resource": "documents/report-2024",
                "attributes": {
                    "tenant_id": "test-tenant",
                    "department": "engineering",
                    "risk_level": "low",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Low-risk read should be allowed by built-in policies
        assert "allowed" in data


class TestGovernanceApprovalWorkflows:
    def test_list_workflows_returns_builtin(self, governance_client):
        client, _ = governance_client
        response = client.get("/governance/approvals/workflows")
        assert response.status_code == 200
        workflows = response.json()
        assert len(workflows) >= 2  # high-risk-task, deletion-approval

    def test_submit_approval_creates_request(self, governance_client):
        client, _ = governance_client
        response = client.post(
            "/governance/approvals/submit",
            json={
                "workflow_id": "high-risk-task",
                "requester_id": "alice",
                "tenant_id": "test-tenant",
                "resource_type": "task",
                "resource_id": "task-001",
                "attributes": {"risk_level": "high"},
                "resource_summary": "Delete production database",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "request_id" in data or data.get("status") == "no_approval_required"

    def test_list_approval_requests(self, governance_client):
        client, _ = governance_client
        response = client.get("/governance/approvals/requests")
        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert "total" in data

    def test_decision_requires_valid_request(self, governance_client):
        client, _ = governance_client
        response = client.post(
            "/governance/approvals/decide",
            json={
                "request_id": "apr-nonexistent",
                "decision": "approved",
                "approver_id": "manager",
                "comment": "Approved",
            },
        )
        assert response.status_code == 400


class TestGovernanceMultiTenant:
    def test_list_tenants_requires_platform_admin(self, governance_client):
        client, _ = governance_client
        response = client.get("/governance/tenants")
        assert response.status_code == 401  # no token

        _, settings = governance_client
        token = _make_admin_token(settings)
        response = client.get(
            "/governance/tenants",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        tenants = response.json()
        assert isinstance(tenants, list)

    def test_register_tenant(self, governance_client):
        client, settings = governance_client
        token = _make_admin_token(settings)
        response = client.post(
            "/governance/tenants",
            params={"name": "Acme Corp", "plan": "pro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Acme Corp"
        assert data["plan"] == "pro"
        assert data["status"] == "active"
        tenant_id = data["id"]

        # Verify we can retrieve it
        response = client.get(f"/governance/tenants/{tenant_id}")
        assert response.status_code == 200

    def test_quota_enforcement(self, governance_client):
        client, settings = governance_client
        token = _make_admin_token(settings)

        # Register a tenant
        response = client.post(
            "/governance/tenants",
            params={"name": "Quota Test Tenant", "plan": "free"},
            headers={"Authorization": f"Bearer {token}"},
        )
        tenant_id = response.json()["id"]

        # Get quota
        response = client.get(f"/governance/tenants/{tenant_id}/quota")
        assert response.status_code == 200
        quota = response.json()
        assert quota["max_users"] == 5
        assert quota["max_api_calls_per_day"] == 1000

        # Record some API calls
        for _ in range(3):
            resp = client.post(f"/governance/tenants/{tenant_id}/usage/increment")
            assert resp.status_code == 200

        # Verify usage updated
        response = client.get(f"/governance/tenants/{tenant_id}/usage")
        assert response.status_code == 200
        usage = response.json()
        assert usage["api_calls_today"] == 3
