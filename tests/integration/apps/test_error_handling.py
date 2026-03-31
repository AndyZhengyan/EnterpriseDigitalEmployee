from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.gateway.main import app

client = TestClient(app)


def test_internal_error_does_not_disclose_details():
    """验证系统内部错误响应是否包含对外的脱敏消息而不是源码细节。"""
    headers = {"Authorization": "Bearer test-token"}
    payload = {"employee_id": "test-agent", "content": "test payload", "task_type": "inquiry"}

    # 使用 patch 让内部逻辑抛出异常，验证全局 handler 处理结果
    with patch("apps.gateway.main._dispatch_to_runtime") as mock_dispatch:
        mock_dispatch.side_effect = Exception("Sensitive System Detail: DB Connection Failed")

        # 显式禁止 TestClient 冒泡异常，确保获取 500 响应给 assert
        inner_client = TestClient(app, raise_server_exceptions=False)
        response = inner_client.post("/gateway/dispatch", json=payload, headers=headers)

    assert response.status_code == 500
    data = response.json()
    details = data.get("error", {}).get("details", "")

    # 验证关键点：包含掩码后的通用消息，不包含原始敏感信息
    assert "An internal error occurred" in details
    assert "Sensitive System Detail" not in details
    assert "Exception" not in details
