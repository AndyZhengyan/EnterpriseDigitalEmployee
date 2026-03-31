import pytest
from fastapi.testclient import TestClient


def test_runtime_app_exists_and_responds_to_health():
    """TDD: 验证 Runtime API 存在且能正确响应健康检查。"""
    try:
        from apps.runtime.main import app
    except ImportError:
        pytest.fail("Runtime main.py or app instance not found")

    client = TestClient(app)
    response = client.get("/runtime/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_runtime_execute_endpoint():
    """TDD: 验证 /runtime/execute 接口定义符合模型。"""
    from apps.runtime.main import app

    client = TestClient(app)

    payload = {
        "employee_id": "test-agent",
        "task_id": "task-test-001",
        "task_type": "inquiry",
        "input": {"query": "hello", "params": {}},
        "context": {"session_id": "sess-01", "user_id": "user-01", "tenant_id": "tenant-01"},
    }
    # 我们期望即使没挂载逻辑，接口路由也已定义
    response = client.post("/runtime/execute", json=payload)
    # 如果没实现逻辑目前可能是 500 或 404，TDD 引导我们去实现它
    assert response.status_code in (200, 201, 202)
    assert "task_id" in response.json()
