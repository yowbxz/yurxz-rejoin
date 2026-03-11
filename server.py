"""
YURXZ REJOIN - Backend Server
Sistem: Python HTTP server + ADB localhost (tanpa root)
Port: 7437
"""

import os, json, time, threading, subprocess, re, base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "accounts": [],
    "check_interval": 30,
    "webhook_url": "",
    "auto_mute": True,
    "auto_low_res": True,
    "floating_window": False,
}

# ─── CONFIG ───────────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ─── ADB ──────────────────────────────────────────────────────────────────────

def adb(cmd, timeout=10):
    try:
        r = subprocess.run(f"adb {cmd}", shell=True,
                           capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except Exception as e:
        return False, str(e)

def adb_shell(cmd, timeout=10):
    return adb(f'shell {cmd}', timeout)

def connect_adb():
    adb("start-server")
    for addr in ["localhost:5555", "127.0.0.1:5555"]:
        ok, out = adb(f"connect {addr}")
        if ok and "connected" in out.lower():
            return True
    ok, out = adb("devices")
    return ok and "device" in out

def is_adb_ready():
    ok, out = adb("devices")
    lines = [l for l in out.splitlines() if "\tdevice" in l]
    return len(lines) > 0

# ─── DEVICE CONTROL ───────────────────────────────────────────────────────────

def force_stop(pkg):
    adb_shell(f"am force-stop {pkg}")
    time.sleep(1)

def launch_ps(link, pkg, floating=False):
    if floating:
        adb_shell("settings put global enable_freeform_support 1")
        adb_shell("settings put global force_resizable_activities 1")
        ok, _ = adb_shell(f'am start --windowingMode 5 -a android.intent.action.VIEW -d "{link}" -p {pkg}')
        if ok: return True
    ok, _ = adb_shell(f'am start -a android.intent.action.VIEW -d "{link}" -p {pkg}')
    return ok

def is_running(pkg):
    ok, out = adb_shell(f"pidof {pkg}")
    return ok and out.strip() != ""

def set_low_res():
    adb_shell("wm size 540x960")
    adb_shell("wm density 120")

def restore_res():
    adb_shell("wm size reset")
    adb_shell("wm density reset")

def mute(pkg):
    adb_shell(f"appops set {pkg} PLAY_AUDIO deny")

def set_low_gfx(pkg):
    xml = "<?xml version='1.0' encoding='utf-8' standalone='yes' ?><map><int name=\"GraphicsQualityLevel\" value=\"1\" /></map>"
    path = f"/data/data/{pkg}/shared_prefs/RobloxGraphicsQuality.xml"
    adb_shell(f"mkdir -p /data/data/{pkg}/shared_prefs")
    adb_shell(f"echo '{xml}' > {path}")

def screencap():
    path = "/sdcard/yurxz_ss.png"
    adb_shell(f"screencap -p {path}")
    ok, _ = adb(f"pull {path} /tmp/yurxz_ss.png")
    if ok and os.path.exists("/tmp/yurxz_ss.png"):
        with open("/tmp/yurxz_ss.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def auto_tap_settings():
    """Auto tap grafik + volume ke minimum di Roblox"""
    time.sleep(8)
    taps = [
        (641,198),(575,530),(207,290),(283,970),
        (210,1220),(480,275),(352,970),(480,1220),(122,390)
    ]
    for x, y in taps:
        adb_shell(f"input tap {x} {y}")
        time.sleep(0.5)

def is_frozen(pkg, samples=3):
    usages = []
    for _ in range(samples):
        ok, out = adb_shell(f"top -n 1 -b | grep {pkg}")
        if ok and out:
            for part in out.split():
                try:
                    val = float(part.replace('%',''))
                    if 0 <= val <= 100:
                        usages.append(val)
                        break
                except: pass
        time.sleep(2)
    if not usages: return False
    return sum(usages)/len(usages) < 0.5

# ─── WEBHOOK ──────────────────────────────────────────────────────────────────

def send_webhook(url, msg, img_b64=None):
    if not url: return
    try:
        if img_b64:
            img_data = base64.b64decode(img_b64)
            requests.post(url, data={"content": msg},
                         files={"file": ("ss.png", img_data, "image/png")}, timeout=10)
        else:
            requests.post(url, json={"content": msg}, timeout=10)
    except: pass

# ─── REJOIN MANAGER ───────────────────────────────────────────────────────────

class RejoinManager:
    def __init__(self):
        self.running   = False
        self.thread    = None
        self.logs      = []
        self.states    = {}   # {index: {name, status, last_check}}
        self.config    = load_config()
        self._lock     = threading.Lock()

    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > 200:
                self.logs = self.logs[-200:]
        print(entry)

    def get_logs(self, since=0):
        with self._lock:
            return self.logs[since:]

    def get_states(self):
        with self._lock:
            return dict(self.states)

    def reload_config(self):
        self.config = load_config()

    def start(self):
        if self.running: return False
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        restore_res()

    def _loop(self):
        self.log("YURXZ Rejoin started")
        cfg = self.config

        # Init ADB
        self.log("Connecting ADB...")
        if connect_adb():
            self.log("ADB connected ✓")
        else:
            self.log("ADB failed — pastikan ADB aktif di device")

        restore_res()

        accounts = cfg.get("accounts", [])
        interval = cfg.get("check_interval", 30)
        webhook  = cfg.get("webhook_url", "")
        do_mute  = cfg.get("auto_mute", True)
        do_res   = cfg.get("auto_low_res", True)
        do_float = cfg.get("floating_window", False)

        # Init states
        with self._lock:
            for i, acc in enumerate(accounts):
                self.states[i] = {
                    "name": acc.get("name", f"Akun {i+1}"),
                    "status": "Idle",
                    "last_check": "-",
                    "pkg": acc.get("package", "com.roblox.client"),
                }

        while self.running:
            accounts = self.config.get("accounts", [])
            for i, acc in enumerate(accounts):
                if not self.running: break

                name = acc.get("name", f"Akun {i+1}")
                pkg  = acc.get("package", "com.roblox.client")
                link = acc.get("ps_link", "")

                self.log(f"Checking {name}...")

                with self._lock:
                    if i not in self.states:
                        self.states[i] = {}
                    self.states[i].update({
                        "name": name,
                        "last_check": time.strftime("%H:%M:%S"),
                        "pkg": pkg,
                    })

                # Cek running
                running = is_running(pkg)

                # Cek freeze
                if running and is_frozen(pkg):
                    self.log(f"{name}: FROZEN! Restarting...")
                    with self._lock:
                        self.states[i]["status"] = "❄️ Frozen"
                    running = False

                if running:
                    self.log(f"{name}: ✓ In Game")
                    with self._lock:
                        self.states[i]["status"] = "✅ In Game"
                else:
                    self.log(f"{name}: Not running — rejoining...")
                    with self._lock:
                        self.states[i]["status"] = "🔄 Rejoining..."

                    force_stop(pkg)

                    if do_res: set_low_gfx(pkg)
                    restore_res()

                    ok = launch_ps(link, pkg, floating=do_float)
                    if ok:
                        self.log(f"{name}: ✓ Launched!")
                        with self._lock:
                            self.states[i]["status"] = "✅ Launched"

                        if do_mute: mute(pkg)
                        if do_res:
                            set_low_res()
                            threading.Thread(target=auto_tap_settings, daemon=True).start()

                        ss = screencap()
                        send_webhook(webhook,
                            f"🎮 **{name}** rejoined!\n⏰ {time.strftime('%H:%M:%S')}", ss)
                    else:
                        self.log(f"{name}: ✗ Launch failed!")
                        with self._lock:
                            self.states[i]["status"] = "❌ Failed"

            if self.running:
                self.log(f"Waiting {interval}s...")
                time.sleep(interval)

        self.log("Stopped.")
        restore_res()

# Global manager
manager = RejoinManager()

# ─── HTTP SERVER ──────────────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # Suppress default logs

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        # API endpoints
        if path == "/api/status":
            self._json({
                "running": manager.running,
                "adb": is_adb_ready(),
                "states": manager.get_states(),
            })
        elif path == "/api/logs":
            qs    = parse_qs(parsed.query)
            since = int(qs.get("since", ["0"])[0])
            self._json({"logs": manager.get_logs(since)})
        elif path == "/api/config":
            self._json(load_config())
        elif path == "/api/start":
            ok = manager.start()
            self._json({"ok": ok})
        elif path == "/api/stop":
            manager.stop()
            self._json({"ok": True})
        elif path == "/api/connect_adb":
            ok = connect_adb()
            self._json({"ok": ok})
        elif path == "/api/screenshot":
            img = screencap()
            self._json({"img": img})
        else:
            # Serve static files
            if path == "/" or path == "":
                path = "/index.html"
            file_path = os.path.join(STATIC_DIR, path.lstrip("/"))
            if os.path.exists(file_path):
                self._file(file_path)
            else:
                self._json({"error": "not found"}, 404)

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        body    = json.loads(self.rfile.read(length)) if length else {}
        parsed  = urlparse(self.path)
        path    = parsed.path

        if path == "/api/config":
            cfg = load_config()
            cfg.update(body)
            save_config(cfg)
            manager.reload_config()
            self._json({"ok": True})
        elif path == "/api/accounts/add":
            cfg = load_config()
            cfg.setdefault("accounts", []).append(body)
            save_config(cfg)
            manager.reload_config()
            self._json({"ok": True})
        elif path == "/api/accounts/delete":
            idx = body.get("index", -1)
            cfg = load_config()
            accs = cfg.get("accounts", [])
            if 0 <= idx < len(accs):
                accs.pop(idx)
                cfg["accounts"] = accs
                save_config(cfg)
                manager.reload_config()
                self._json({"ok": True})
            else:
                self._json({"ok": False})
        else:
            self._json({"error": "not found"}, 404)

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path):
        ext  = os.path.splitext(path)[1]
        mime = {".html":"text/html",".js":"application/javascript",
                ".css":"text/css",".png":"image/png",".ico":"image/x-icon"}.get(ext,"text/plain")
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

def start_server(port=7437):
    os.makedirs(STATIC_DIR, exist_ok=True)
    httpd = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[YURXZ] Server running at http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    start_server()
