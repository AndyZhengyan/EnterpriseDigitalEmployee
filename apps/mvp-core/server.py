#!/usr/bin/env python3
import json
import random
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = 8100

BASE_LAT = 31.2304
BASE_LNG = 121.4737

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
    "alerts": [],
    "scenario": {
        "incident": None,
        "assets": {
            "recon_drone": {"id": "recon_drone", "type": "recon_drone", "name": "侦查无人机-01", "status": "巡航中", "lat": BASE_LAT + 0.02, "lng": BASE_LNG - 0.03},
            "fire_drone": {"id": "fire_drone", "type": "fire_drone", "name": "消防无人机-01", "status": "待命", "lat": BASE_LAT - 0.01, "lng": BASE_LNG + 0.02},
            "rescue_dog": {"id": "rescue_dog", "type": "rescue_dog", "name": "救援无人狗-01", "status": "待命", "lat": BASE_LAT - 0.015, "lng": BASE_LNG - 0.01},
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


def create_task(task_type: str, payload: dict):
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task = {
        "id": task_id,
        "employee_id": "eda_highway_001",
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


def move_asset(asset_id, target_lat, target_lng, status, duration=6):
    def _run():
        with state_lock:
            asset = state["scenario"]["assets"][asset_id]
            start_lat, start_lng = asset["lat"], asset["lng"]
            asset["status"] = status
        for i in range(1, duration + 1):
            t = i / duration
            with state_lock:
                asset = state["scenario"]["assets"][asset_id]
                asset["lat"] = start_lat + (target_lat - start_lat) * t
                asset["lng"] = start_lng + (target_lng - start_lng) * t
                state["scenario"]["last_updated"] = now()
            time.sleep(1)

    threading.Thread(target=_run, daemon=True).start()


def run_agent_task(task_id: str):
    with state_lock:
        task = state["tasks"].get(task_id)
        if not task:
            return
        task["status"] = "running"
        task["started_at"] = now()
        task["updated_at"] = now()

    try:
        # plan
        with state_lock:
            task = state["tasks"][task_id]
            append_step(task, "Plan", "running", {"message": "识别事故并规划协同处置流程"})
            scenario_log(f"任务 {task_id}：PiAgent 开始规划处置流程。")
        time.sleep(1)

        # detect/recon
        with state_lock:
            task = state["tasks"][task_id]
            lat = task["input"].get("lat", BASE_LAT + random.uniform(-0.01, 0.01))
            lng = task["input"].get("lng", BASE_LNG + random.uniform(-0.01, 0.01))
            state["scenario"]["incident"] = {
                "id": f"INC-{int(now())}",
                "type": "高速交通事故",
                "status": "已发现",
                "lat": lat,
                "lng": lng,
            }
            append_step(task, "Recon", "success", {"incident": state["scenario"]["incident"]})
            scenario_log("侦查无人机发现事故点，开始盘旋侦查。")
        move_asset("recon_drone", lat, lng, "盘旋侦查", duration=5)
        time.sleep(2)

        # firefighting
        with state_lock:
            task = state["tasks"][task_id]
            incident = state["scenario"]["incident"]
            append_step(task, "Dispatch Fire Drone", "running", {"target": incident})
            scenario_log("消防无人机启动，前往事故点灭火。")
        move_asset("fire_drone", incident["lat"] + 0.0015, incident["lng"] - 0.0015, "灭火作业", duration=7)
        time.sleep(2)

        # rescue dog
        with state_lock:
            task = state["tasks"][task_id]
            incident = state["scenario"]["incident"]
            append_step(task, "Dispatch Rescue Dog", "running", {"target": incident})
            scenario_log("救援无人狗出发，执行伤员定位与现场救援。")
        move_asset("rescue_dog", incident["lat"] - 0.001, incident["lng"] + 0.001, "现场搜救", duration=9)
        time.sleep(3)

        # review/finish
        with state_lock:
            task = state["tasks"][task_id]
            incident = state["scenario"]["incident"]
            incident["status"] = "处置中"
            append_step(task, "Review", "success", {"message": "火情受控，救援进行中"})
            scenario_log("PiAgent 复核：火情受控，救援进展正常。")
        time.sleep(2)

        with state_lock:
            task = state["tasks"][task_id]
            incident = state["scenario"]["incident"]
            incident["status"] = "已完成"
            state["scenario"]["assets"]["recon_drone"]["status"] = "返航"
            state["scenario"]["assets"]["fire_drone"]["status"] = "返航"
            state["scenario"]["assets"]["rescue_dog"]["status"] = "待命"
            append_step(task, "Complete", "success", {"message": "任务闭环完成"})
            task["status"] = "succeeded"
            task["result"] = {"summary": "事故处置完成，设备返航/待命。", "incident": incident}
            task["finished_at"] = now()
            task["updated_at"] = now()
            scenario_log("任务闭环完成。")
            emp = state["employees"][task["employee_id"]]
            emp["success_count"] += 1
            emp["active_task_count"] = max(0, emp["active_task_count"] - 1)
            emp["updated_at"] = now()
    except Exception as exc:
        with state_lock:
            task = state["tasks"].get(task_id)
            if task:
                task["status"] = "failed"
                task["error"] = str(exc)
                task["finished_at"] = now()
                task["updated_at"] = now()
                append_step(task, "Failed", "failed", {"error": str(exc)})
                state["alerts"].append({
                    "id": f"alert_{uuid.uuid4().hex[:8]}",
                    "severity": "high",
                    "type": "task_failed",
                    "task_id": task_id,
                    "message": f"任务失败: {exc}",
                    "created_at": now(),
                    "status": "open",
                })
                emp = state["employees"][task["employee_id"]]
                emp["failure_count"] += 1
                emp["active_task_count"] = max(0, emp["active_task_count"] - 1)
                emp["updated_at"] = now()


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
                state["scenario"]["assets"]["recon_drone"].update({"status": "巡航中", "lat": BASE_LAT + 0.02, "lng": BASE_LNG - 0.03})
                state["scenario"]["assets"]["fire_drone"].update({"status": "待命", "lat": BASE_LAT - 0.01, "lng": BASE_LNG + 0.02})
                state["scenario"]["assets"]["rescue_dog"].update({"status": "待命", "lat": BASE_LAT - 0.015, "lng": BASE_LNG - 0.01})
                scenario_log("场景已重置。")
            return self._json({"ok": True})

        self.send_error(404)


def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"MVP core running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
