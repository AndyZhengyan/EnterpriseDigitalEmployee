#!/usr/bin/env python3
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = 8000

BASE_LAT = 31.2304
BASE_LNG = 121.4737

state = {
    "last_updated": time.time(),
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
    "logs": [
        {"ts": time.time(), "message": "系统已启动，等待事件..."}
    ],
}


def log(msg):
    state["logs"].append({"ts": time.time(), "message": msg})
    state["logs"] = state["logs"][-100:]
    state["last_updated"] = time.time()


def move_asset(asset_id, target_lat, target_lng, status, duration=8):
    asset = state["assets"][asset_id]
    start_lat, start_lng = asset["lat"], asset["lng"]
    steps = max(duration, 1)

    def _run():
        asset["status"] = status
        for i in range(1, steps + 1):
            t = i / steps
            asset["lat"] = start_lat + (target_lat - start_lat) * t
            asset["lng"] = start_lng + (target_lng - start_lng) * t
            state["last_updated"] = time.time()
            time.sleep(1)

    th = threading.Thread(target=_run, daemon=True)
    th.start()


def run_demo_flow(incident_lat, incident_lng):
    incident_id = f"INC-{int(time.time())}"
    state["incident"] = {
        "id": incident_id,
        "type": "交通事故",
        "status": "已发现",
        "lat": incident_lat,
        "lng": incident_lng,
    }
    log(f"{incident_id} 侦查无人机发现高速事故点。")

    move_asset("recon_drone", incident_lat, incident_lng, "盘旋侦查", duration=5)

    def stage2():
        state["assets"]["fire_drone"]["status"] = "已起飞"
        log("消防无人机启动，前往事故点灭火。")
        move_asset("fire_drone", incident_lat + 0.0015, incident_lng - 0.0015, "灭火作业", duration=7)

    def stage3():
        state["assets"]["rescue_dog"]["status"] = "已出发"
        log("救援无人狗前往事故点，执行现场救援与伤员定位。")
        move_asset("rescue_dog", incident_lat - 0.001, incident_lng + 0.001, "现场搜救", duration=9)

    def stage4():
        if state["incident"]:
            state["incident"]["status"] = "处置中"
        log("事故处置进行中：火情受控，救援进展正常。")

    def stage5():
        if state["incident"]:
            state["incident"]["status"] = "已完成"
        state["assets"]["recon_drone"]["status"] = "返航"
        state["assets"]["fire_drone"]["status"] = "返航"
        state["assets"]["rescue_dog"]["status"] = "待命"
        log("事故处置完成，设备返航/待命，任务闭环结束。")

    threading.Timer(3, stage2).start()
    threading.Timer(6, stage3).start()
    threading.Timer(12, stage4).start()
    threading.Timer(20, stage5).start()


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type="text/html; charset=utf-8"):
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._json(state)
            return
        if parsed.path == "/api/health":
            self._json({"ok": True, "ts": time.time()})
            return

        static_root = Path(__file__).parent / "static"
        request_path = parsed.path or "/"
        if request_path == "/":
            target = static_root / "index.html"
        else:
            relative = request_path.lstrip("/")
            target = static_root / relative
            if request_path.endswith("/"):
                target = target / "index.html"

        if target.exists() and target.is_file() and static_root in target.parents:
            suffix_map = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "text/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
            }
            self._serve_file(target, suffix_map.get(target.suffix, "text/plain; charset=utf-8"))
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/incidents/mock":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            payload = json.loads(body) if body else {}
            lat = payload.get("lat", BASE_LAT + random.uniform(-0.01, 0.01))
            lng = payload.get("lng", BASE_LNG + random.uniform(-0.01, 0.01))
            run_demo_flow(lat, lng)
            self._json({"ok": True, "incident": state["incident"]})
            return
        if parsed.path == "/api/reset":
            state["incident"] = None
            state["assets"]["recon_drone"].update({"status": "巡航中", "lat": BASE_LAT + 0.02, "lng": BASE_LNG - 0.03})
            state["assets"]["fire_drone"].update({"status": "待命", "lat": BASE_LAT - 0.01, "lng": BASE_LNG + 0.02})
            state["assets"]["rescue_dog"].update({"status": "待命", "lat": BASE_LAT - 0.015, "lng": BASE_LNG - 0.01})
            log("系统已重置。")
            self._json({"ok": True})
            return
        self.send_error(404)


def main():
    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"Highway rescue demo running at http://{HOST}:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
