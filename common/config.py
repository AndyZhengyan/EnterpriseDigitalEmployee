import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class OpenClawSettings(BaseSettings):
    """OpenClaw Gateway 配置"""

    # Gateway 基础连接
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 18789
    gateway_token: Optional[str] = None

    # 握手身份标识
    client_id: str = "cli"
    client_mode: str = "cli"
    platform: str = "darwin"
    version: str = "2026.03.29"

    # 权限范围
    default_scopes: List[str] = [
        "operator.read",
        "operator.admin",
        "operator.write",
        "operator.approvals",
        "operator.pairing",
    ]

    # 身份文件路径（可选覆盖）
    identity_dir: str = os.path.expanduser("~/.openclaw/identity")
    config_file: str = os.path.expanduser("~/.openclaw/openclaw.json")

    class Config:
        env_prefix = "OPENCLAW_"
        case_sensitive = False


class PiAgentSidecarConfig(BaseSettings):
    """PiAgent Sidecar 配置"""

    enabled: bool = False  # False=subprocess 模式, True=sidecar 模式
    socket_path: str = "/tmp/piagent.sock"
    startup_timeout_ms: int = 10_000
    request_timeout_ms: int = 300_000
    sidecar_script: Optional[str] = None

    class Config:
        env_prefix = "PIAGENT_SIDECAR_"
        case_sensitive = False


class RuntimeSettings(BaseSettings):
    """Runtime 模块全局配置"""

    max_concurrent_tasks: int = 100
    task_timeout_seconds: int = 30
    step_timeout_seconds: int = 10

    # 子模块配置
    openclaw: OpenClawSettings = OpenClawSettings()
    piagent_sidecar: PiAgentSidecarConfig = PiAgentSidecarConfig()

    class Config:
        env_prefix = "RUNTIME_"
        case_sensitive = False


# 全局配置实例
settings = RuntimeSettings()
