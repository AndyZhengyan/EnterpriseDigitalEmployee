#!/usr/bin/env python3
import json
import os
import random
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = 8100

BASE_LAT = 31.2304
BASE_LNG = 121.4737

# Preferred path: keep PiAgent runtime untouched and call it via bridge API.
PIAGENT_PLANNER_URL = os.getenv("PIAGENT_PLANNER_URL", "").strip()
PIAGENT_API_KEY = os.getenv("PIAGENT_API_KEY", "").strip()

# Optional fallback path: OpenAI-compatible planner.
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

MODEL_TIMEOUT_SEC = float(os.getenv("MODEL_TIMEOUT_SEC", "35"))
MODEL_MAX_RETRY = int(os.getenv("MODEL_MAX_RETRY", "2"))

state_lock = threading.Lock()

state = {
    "employees": {
        "eda_highway_001": {
            "id": "eda_highway_001",
            "name": "高速应急数字员工-01",
            "role": "高速事故处置协调员",
            "status": "online",
            "active_task_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "handoff_count": 0,
            "updated_at": time.time(),
        }
    },
    "tasks": {},
    "commands": [],
    "audit_logs": [],
    "alerts": [],
    "agent_runtime": {
        "agent_id": "enterprise_orchestrator_001",
        "engine": "Enterprise-Orchestrator",
        "status": "online",
        "last_heartbeat": time.time(),
        "issued_command_count": 0,
        "planner_backends": {
            "piagent_bridge_enabled": bool(PIAGENT_PLANNER_URL),
            "openai_compat_enabled": bool(OPENAI_API_KEY),
        },
        "last_plan_call": None,
    },
    "scenario": {
        "incident": None,
        "assets": {
            "recon_drone": {
                "id": "recon_drone",
                "type": "recon_drone",
                "name": "侦查无人机-01",
                "status": "巡航中",
                "lat": BASE_LAT + 0.02,
                "lng": BASE_LNG - 0.03,
            },
            "fire_drone": {
                "id": "fire_drone",
                "type": "fire_drone",
                "name": "消防无人机-01",
                "status": "待命",
                "lat": BASE_LAT - 0.01,
                "lng": BASE_LNG + 0.02,
            },
            "rescue_dog": {
                "id": "rescue_dog",
                "type": "rescue_dog",
                "name": "救援无人狗-01",
                "status": "待命",
                "lat": BASE_LAT - 0.015,
                "lng": BASE_LNG - 0.01,
            },
        },
        "logs": [{"ts": time.time(), "message": "系统初始化完成，待命中。"}],
        "last_updated": time.time(),
    },
}


def now():
    return time.time()


def scenario_log(message: str):
    sc = state["scenario"]
    sc["logs"].append({"ts": now(), "message": message})
    sc["logs"] = sc["logs"][-120:]
    sc["last_updated"] = now()


def append_audit(action: str, target: str, result: str, trace_id: str, actor_type="agent", detail=None):
    state["audit_logs"].append(
        {
            "id": f"audit_{uuid.uuid4().hex[:8]}",
            "trace_id": trace_id,
            "actor_type": actor_type,
            "action": action,
            "target": target,
            "result": result,
            "detail": detail or {},
            "timestamp": now(),
        }
    )
    state["audit_logs"] = state["audit_logs"][-200:]


def append_alert(alert_type: str, message: str, severity="medium", task_id=None):
    state["alerts"].append(
        {
            "id": f"alert_{uuid.uuid4().hex[:8]}",
            "severity": severity,
            "type": alert_type,
            "task_id": task_id,
            "message": message,
            "created_at": now(),
            "status": "open",
        }
    )
    state["alerts"] = state["alerts"][-100:]


def emit_command(task_id: str, trace_id: str, asset_id: str, action: str, target=None):
    cmd = {
        "id": f"cmd_{uuid.uuid4().hex[:8]}",
        "task_id": task_id,
        "trace_id": trace_id,
        "issued_by": state["agent_runtime"]["agent_id"],
        "asset_id": asset_id,
        "action": action,
        "target": target or {},
        "status": "sent",
        "created_at": now(),
        "updated_at": now(),
        "executed_at": None,
    }
    state["commands"].append(cmd)
    state["commands"] = state["commands"][-300:]
    state["agent_runtime"]["last_heartbeat"] = now()
    state["agent_runtime"]["issued_command_count"] += 1
    append_audit(
        action="issue_command",
        target=f"{asset_id}:{action}",
        result="sent",
        trace_id=trace_id,
        detail={"task_id": task_id, "command_id": cmd["id"]},
    )
    return cmd


def execute_mock_command(command: dict, duration=6):
    def _run():
        with state_lock:
            command["status"] = "executing"
            command["updated_at"] = now()
            asset = state["scenario"]["assets"][command["asset_id"]]
            start_lat, start_lng = asset["lat"], asset["lng"]
            target = command["target"]
            target_lat = target.get("lat", start_lat)
            target_lng = target.get("lng", start_lng)
            asset["status"] = command["action"]

        for i in range(1, duration + 1):
            t = i / duration
            with state_lock:
                asset = state["scenario"]["assets"][command["asset_id"]]
                asset["lat"] = start_lat + (target_lat - start_lat) * t
                asset["lng"] = start_lng + (target_lng - start_lng) * t
                state["scenario"]["last_updated"] = now()
            time.sleep(1)

        with state_lock:
            command["status"] = "acked"
            command["updated_at"] = now()
            command["executed_at"] = now()
            append_audit(
                action="command_ack",
                target=f"{command['asset_id']}:{command['action']}",
                result="acked",
                trace_id=command["trace_id"],
                actor_type="system",
                detail={"command_id": command["id"], "task_id": command["task_id"]},
            )

    threading.Thread(target=_run, daemon=True).start()


def extract_json_block(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    return cleaned


def fallback_plan(payload: dict):
    lat = payload.get("lat", BASE_LAT + random.uniform(-0.01, 0.01))
    lng = payload.get("lng", BASE_LNG + random.uniform(-0.01, 0.01))
    return {
        "summary": "按标准高速事故SOP执行侦查、灭火与搜救。",
        "risk_level": "medium",
        "commands": [
            {"asset_id": "recon_drone", "action": "盘旋侦查", "target": {"lat": lat, "lng": lng}},
            {
                "asset_id": "fire_drone",
                "action": "灭火作业",
                "target": {"lat": lat + 0.0015, "lng": lng - 0.0015},
            },
            {
                "asset_id": "rescue_dog",
                "action": "现场搜救",
                "target": {"lat": lat - 0.001, "lng": lng + 0.001},
            },
        ],
        "notes": ["planner 不可用，已启用内置应急SOP"],
    }


def _build_plan_request_payload(task_payload: dict):
    tools = [
        {"asset_id": "recon_drone", "actions": ["盘旋侦查", "返航"]},
        {"asset_id": "fire_drone", "actions": ["灭火作业", "返航"]},
        {"asset_id": "rescue_dog", "actions": ["现场搜救", "返回待命"]},
    ]
    return {
        "task_type": "highway_incident_response",
        "task_input": task_payload,
        "available_tools": tools,
        "response_schema": {
            "summary": "string",
            "risk_level": "low|medium|high",
            "commands": "[{asset_id, action, target:{lat,lng}}]",
            "notes": "string[]",
        },
    }


def call_piagent_bridge(task_payload: dict):
    if not PIAGENT_PLANNER_URL:
        raise RuntimeError("PIAGENT_PLANNER_URL is not configured")

    req_body = _build_plan_request_payload(task_payload)
    headers = {"Content-Type": "application/json"}
    if PIAGENT_API_KEY:
        headers["Authorization"] = f"Bearer {PIAGENT_API_KEY}"

    req = urllib.request.Request(
        PIAGENT_PLANNER_URL,
        data=json.dumps(req_body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=MODEL_TIMEOUT_SEC) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # Expected bridge response:
    # { "plan": {summary, risk_level, commands, notes}, "meta": {...} }
    plan = data.get("plan") if isinstance(data, dict) else None
    if not isinstance(plan, dict):
        raise RuntimeError("piagent bridge returned invalid plan")
    if not isinstance(plan.get("commands"), list) or not plan.get("commands"):
        raise RuntimeError("piagent bridge returned empty commands")
    return {"plan": plan, "meta": data.get("meta", {})}


def build_openai_messages(task_payload: dict):
    req_payload = _build_plan_request_payload(task_payload)
    system_prompt = (
        "你是高速事故处置数字员工的调度规划器。"
        "请只输出JSON对象，不要输出额外解释。"
        "字段必须包含：summary(string),risk_level(low|medium|high),"
        "commands(array),notes(array string)。"
        "commands 每项必须包含 asset_id,action,target(lat,lng)。"
        "只能使用给定资产和动作。"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(req_payload, ensure_ascii=False)},
    ]


def call_openai_compat(task_payload: dict):
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    request_body = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "messages": build_openai_messages(task_payload),
    }
    req = urllib.request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=MODEL_TIMEOUT_SEC) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    text = data["choices"][0]["message"]["content"]
    plan = json.loads(extract_json_block(text))
    commands = plan.get("commands")
    if not isinstance(commands, list) or len(commands) == 0:
        raise RuntimeError("openai planner returned empty commands")
    return {
        "plan": plan,
        "meta": {
            "provider": "openai-compatible",
            "model": data.get("model", OPENAI_MODEL),
            "usage": data.get("usage", {}),
        },
    }


def _record_plan_result(trace_id: str, backend: str, ok: bool, detail=None):
    with state_lock:
        state["agent_runtime"]["last_plan_call"] = {
            "trace_id": trace_id,
            "backend": backend,
            "ok": ok,
            "at": now(),
            "detail": detail or {},
        }
        append_audit(
            "planner_call",
            backend,
            "ok" if ok else "failed",
            trace_id,
            detail=detail or {},
        )


def generate_plan(task_payload: dict, trace_id: str):
    backends = [
        ("piagent_bridge", call_piagent_bridge),
        ("openai_compat", call_openai_compat),
    ]

    errors = []
    for backend_name, backend_fn in backends:
        for attempt in range(1, MODEL_MAX_RETRY + 1):
            started = now()
            try:
                result = backend_fn(task_payload)
                latency_ms = int((now() - started) * 1000)
                _record_plan_result(
                    trace_id,
                    backend_name,
                    True,
                    {
                        "attempt": attempt,
                        "latency_ms": latency_ms,
                        "meta": result.get("meta", {}),
                    },
                )
                return result["plan"], backend_name
            except Exception as exc:
                last_error = str(exc)
                errors.append({"backend": backend_name, "attempt": attempt, "error": last_error})
                _record_plan_result(
                    trace_id,
                    backend_name,
                    False,
                    {"attempt": attempt, "error": last_error},
                )
                if attempt < MODEL_MAX_RETRY:
                    time.sleep(0.8 * attempt)

    with state_lock:
        append_alert("planner_fallback", f"规划器不可用，使用回退策略：{errors[-1]['error']}", "medium")
    return fallback_plan(task_payload), "fallback_sop"


def create_task(task_type: str, payload: dict):
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "employee_id": "eda_highway_001",
        "trace_id": f"tr_{uuid.uuid4().hex[:10]}",
        "task_type": task_type,
        "status": "queued",
        "priority": payload.get("priority", "P1"),
        "input": payload,
        "result": None,
        "error": None,
        "steps": [],
        "created_at": now(),
        "updated_at": now(),
        "started_at": None,
        "finished_at": None,
    }
    with state_lock:
        state["tasks"][task_id] = task
        emp = state["employees"][task["employee_id"]]
        emp["active_task_count"] += 1
        emp["updated_at"] = now()
        append_audit("create_task", task_id, "accepted", task["trace_id"], actor_type="user")
    threading.Thread(target=run_agent_task, args=(task_id,), daemon=True).start()
    return task


def append_step(task, name, status="running", detail=None):
    step = {
        "id": f"step_{uuid.uuid4().hex[:6]}",
        "name": name,
        "status": status,
        "detail": detail or {},
        "ts": now(),
    }
    task["steps"].append(step)
    task["updated_at"] = now()
    return step


def normalize_command(command: dict, incident: dict):
    asset_id = command.get("asset_id")
    if asset_id not in state["scenario"]["assets"]:
        return None
    action = command.get("action") or "执行任务"
    target = command.get("target") if isinstance(command.get("target"), dict) else {}
    lat = target.get("lat", incident["lat"])
    lng = target.get("lng", incident["lng"])
    return {"asset_id": asset_id, "action": action, "target": {"lat": lat, "lng": lng}}


def run_agent_task(task_id: str):
    with state_lock:
        task = state["tasks"].get(task_id)
        if not task:
            return
        task["status"] = "running"
        task["started_at"] = now()
        task["updated_at"] = now()

    try:
        with state_lock:
            task = state["tasks"][task_id]
            trace_id = task["trace_id"]
            payload = dict(task["input"])
            append_step(task, "Plan", "running", {"message": "调用外部规划器（优先 PiAgent Bridge）"})
            scenario_log(f"任务 {task_id}：Orchestrator 开始规划处置流程。")
            append_audit("plan", task_id, "start", trace_id)

        plan, plan_source = generate_plan(payload, trace_id)
        lat = payload.get("lat", BASE_LAT + random.uniform(-0.01, 0.01))
        lng = payload.get("lng", BASE_LNG + random.uniform(-0.01, 0.01))

        with state_lock:
            task = state["tasks"][task_id]
            incident = {
                "id": f"INC-{int(now())}",
                "type": "高速交通事故",
                "status": "已发现",
                "lat": lat,
                "lng": lng,
            }
            state["scenario"]["incident"] = incident
            append_step(task, "Plan", "success", {"source": plan_source, "plan": plan})
            scenario_log(f"规划完成（{plan_source}），开始执行调度命令。")

            if str(plan.get("risk_level", "")).lower() == "high":
                append_alert("high_risk", f"任务 {task_id} 风险等级高，建议人工复核。", "high", task_id=task_id)
                emp = state["employees"][task["employee_id"]]
                emp["handoff_count"] += 1

            append_step(task, "Recon", "success", {"incident": incident})

        issued = []
        for cmd_payload in plan.get("commands", []):
            with state_lock:
                incident = state["scenario"]["incident"]
                normalized = normalize_command(cmd_payload, incident)
                if not normalized:
                    append_audit(
                        "skip_command",
                        "unknown_asset",
                        "ignored",
                        trace_id,
                        detail={"command": cmd_payload},
                    )
                    continue
                task = state["tasks"][task_id]
                append_step(task, f"Dispatch {normalized['asset_id']}", "running", normalized)
                scenario_log(f"{normalized['asset_id']} 执行动作：{normalized['action']}。")
                cmd = emit_command(task_id, trace_id, normalized["asset_id"], normalized["action"], normalized["target"])
                execute_mock_command(cmd, duration=5)
                issued.append(cmd)
            time.sleep(1)

        with state_lock:
            task = state["tasks"][task_id]
            incident = state["scenario"]["incident"]
            incident["status"] = "已完成"
            state["scenario"]["assets"]["recon_drone"]["status"] = "返航"
            state["scenario"]["assets"]["fire_drone"]["status"] = "返航"
            state["scenario"]["assets"]["rescue_dog"]["status"] = "待命"
            append_step(task, "Review", "success", {"message": "复核通过，任务完成"})
            append_step(task, "Complete", "success", {"issued_command_count": len(issued)})
            task["status"] = "succeeded"
            task["result"] = {
                "summary": plan.get("summary", "事故处置完成"),
                "incident": incident,
                "plan_source": plan_source,
                "risk_level": plan.get("risk_level", "unknown"),
                "notes": plan.get("notes", []),
            }
            task["finished_at"] = now()
            task["updated_at"] = now()
            scenario_log("任务闭环完成。")
            emp = state["employees"][task["employee_id"]]
            emp["success_count"] += 1
            emp["active_task_count"] = max(0, emp["active_task_count"] - 1)
            emp["updated_at"] = now()
            append_audit("complete", task_id, "succeeded", trace_id)
    except Exception as exc:
        with state_lock:
            task = state["tasks"].get(task_id)
            if task:
                task["status"] = "failed"
                task["error"] = str(exc)
                task["finished_at"] = now()
                task["updated_at"] = now()
                append_step(task, "Failed", "failed", {"error": str(exc)})
                append_alert("task_failed", f"任务失败: {exc}", "high", task_id=task_id)
                emp = state["employees"][task["employee_id"]]
                emp["failure_count"] += 1
                emp["active_task_count"] = max(0, emp["active_task_count"] - 1)
                emp["updated_at"] = now()
                append_audit("complete", task_id, "failed", task.get("trace_id", "tr_unknown"), detail={"error": str(exc)})


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve(self, fp: Path, content_type="text/html; charset=utf-8"):
        if not fp.exists():
            self.send_error(404)
            return
        data = fp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path
        if p == "/api/health":
            return self._json({"ok": True, "ts": now()})
        if p == "/api/employees":
            with state_lock:
                employees = list(state["employees"].values())
            return self._json({"items": employees})
        if p == "/api/tasks":
            with state_lock:
                tasks = sorted(state["tasks"].values(), key=lambda x: x["created_at"], reverse=True)
            return self._json({"items": tasks})
        if p.startswith("/api/tasks/"):
            tid = p.split("/")[-1]
            with state_lock:
                task = state["tasks"].get(tid)
            if not task:
                return self._json({"error": "not found"}, 404)
            return self._json(task)
        if p == "/api/scenario":
            with state_lock:
                sc = state["scenario"]
            return self._json(sc)
        if p == "/api/alerts":
            with state_lock:
                alerts = list(reversed(state["alerts"][-50:]))
            return self._json({"items": alerts})
        if p == "/api/commands":
            with state_lock:
                commands = list(reversed(state["commands"][-100:]))
            return self._json({"items": commands})
        if p == "/api/audit-logs":
            with state_lock:
                logs = list(reversed(state["audit_logs"][-100:]))
            return self._json({"items": logs})
        if p == "/api/agent-runtime":
            with state_lock:
                rt = dict(state["agent_runtime"])
            return self._json(rt)
        if p == "/":
            return self._serve(Path(__file__).parent / "static" / "index.html")
        if p == "/console":
            return self._serve(Path(__file__).parent / "static" / "console.html")
        if p == "/scenario":
            return self._serve(Path(__file__).parent / "static" / "scenario.html")
        if p.startswith("/static/"):
            fp = Path(__file__).parent / p.lstrip("/")
            ctype = "text/plain; charset=utf-8"
            if fp.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"
            elif fp.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            elif fp.suffix == ".html":
                ctype = "text/html; charset=utf-8"
            return self._serve(fp, ctype)
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}

        if parsed.path == "/api/tasks":
            task_type = payload.get("task_type", "highway_incident_response")
            task = create_task(task_type, payload)
            return self._json(task, 201)

        if parsed.path == "/api/scenario/reset":
            with state_lock:
                state["scenario"]["incident"] = None
                state["scenario"]["assets"]["recon_drone"].update(
                    {"status": "巡航中", "lat": BASE_LAT + 0.02, "lng": BASE_LNG - 0.03}
                )
                state["scenario"]["assets"]["fire_drone"].update(
                    {"status": "待命", "lat": BASE_LAT - 0.01, "lng": BASE_LNG + 0.02}
                )
                state["scenario"]["assets"]["rescue_dog"].update(
                    {"status": "待命", "lat": BASE_LAT - 0.015, "lng": BASE_LNG - 0.01}
                )
                scenario_log("场景已重置。")
            return self._json({"ok": True})

        self.send_error(404)


def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"MVP core running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
