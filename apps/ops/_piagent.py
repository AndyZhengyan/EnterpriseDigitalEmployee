# apps/ops/_piagent.py — PiAgent CLI runner and helpers
# Extracted from main.py to avoid circular imports with routers.
import json
import os
import subprocess
import uuid
from typing import Any, Dict

_log = None  # lazy import below


def _get_logger():
    global _log
    if _log is None:
        from common.tracing import get_logger

        _log = get_logger("ops")
    return _log


def _get_gateway_token() -> str:
    """Read gateway token from openclaw config or env."""
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if token:
        return token
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
            token = cfg.get("gateway", {}).get("auth", {}).get("token", "")
            if not token:
                _get_logger().warning("openclaw_gateway_token_empty", path=config_path)
            return token
    except FileNotFoundError:
        _get_logger().warning("openclaw_config_not_found", path=config_path)
        return ""
    except Exception:
        _get_logger().warning("openclaw_config_read_failed", path=config_path)
        return ""


def _normalize_openclaw_id(agent_id: str) -> str:
    """Strip non-ASCII chars so openclaw can find the normalized agent ID.

    openclaw normalizes agent IDs (removes Chinese/non-ASCII chars) when they are
    registered via `openclaw agents add`. For example, 'av-行政专员-123'
    becomes 'av---123'. We must use the normalized form when calling openclaw.
    """
    return agent_id.encode("ascii", "ignore").decode("ascii")


def _run_piagent(message: str, agent_id: str = "chat", timeout: int = 60) -> Dict[str, Any]:
    """Call openclaw CLI (pi-agent) and return parsed JSON result. Stub for CI."""
    # CI stub — openclaw CLI not available in GitHub Actions runner
    if os.environ.get("PIAGENT_CLI_STUB") == "true":
        return {
            "status": "ok",
            "runId": f"stub-{uuid.uuid4().hex[:8]}",
            "summary": "CI stub response — this is a simulated agent execution",
            "result": {
                "meta": {
                    "agentMeta": {
                        "usage": {"input": 1200, "output": 340, "cacheRead": 0},
                        "durationMs": 2100,
                    }
                }
            },
        }

    normalized_id = _normalize_openclaw_id(agent_id)
    token = _get_gateway_token()
    gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "OPENCLAW_GATEWAY_TOKEN": token,
        "OPENCLAW_GATEWAY_URL": gateway_url,
    }
    try:
        result = subprocess.run(
            [
                "openclaw",
                "agent",
                "--agent",
                normalized_id,
                "--message",
                message,
                "--json",
                "--thinking",
                "medium",
                "--timeout",
                str(timeout),
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            env=env,
            check=False,
        )
        stdout_output = result.stdout.strip()
        if not stdout_output:
            fallback_output = result.stderr.strip()
            if not fallback_output:
                return {"status": "error", "summary": "Empty response", "usage": {}}
            json_start = fallback_output.find("{")
            if json_start == -1:
                if result.returncode == 0:
                    return {
                        "status": "error",
                        "summary": f"No JSON in output: {fallback_output[:200]}",
                        "usage": {},
                    }
                return {"status": "error", "summary": f"CLI error: {fallback_output[:200]}", "usage": {}}
            parsed = json.loads(fallback_output[json_start:])
        else:
            parsed = json.loads(stdout_output)
        result_block = parsed.get("result", {})
        payloads = result_block.get("payloads")
        text = (
            payloads[0].get("text", "")
            if payloads
            else result_block.get("meta", {}).get("finalAssistantVisibleText", "")
        )
        if text == "NO_REPLY":
            text = ""
        parsed["responseText"] = text
        return parsed
    except FileNotFoundError:
        _get_logger().error("openclaw_cli_not_found", agent_id=normalized_id)
        return {"status": "error", "summary": "openclaw CLI not found in PATH", "usage": {}}
    except subprocess.TimeoutExpired:
        _get_logger().warning("piagent_timeout", agent_id=normalized_id, timeout=timeout)
        return {"status": "error", "summary": "Execution timed out", "usage": {}}
    except json.JSONDecodeError as e:
        _get_logger().error("piagent_json_error", agent_id=normalized_id, error=str(e))
        return {"status": "error", "summary": f"Invalid JSON: {e}", "usage": {}}
    except Exception as e:
        _get_logger().error("piagent_unexpected_error", agent_id=normalized_id, error=str(e))
        return {"status": "error", "summary": str(e), "usage": {}}
