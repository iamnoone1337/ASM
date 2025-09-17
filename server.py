#!/usr/bin/env python3
"""
Backend server for subdomain enumeration and monitoring

Features:
- Basic Authentication (credentials from auth.json or AUTH_FILE)
- Subdomain discovery sources:
  - crt.sh via /api/crt
  - Wayback Machine (CDX) via /api/wayback
  - Subfinder via /api/subfinder (optional; requires subfinder installed)
- HTTP metadata (status/title) via /api/meta
- Monitoring automation:
  - Manage monitors via /api/monitor (GET/POST/DELETE)
  - Background rescans every interval_hours (default 12)
  - New-asset events recorded and retrievable via /api/monitor/updates?since=<ISO8601>

Environment:
- HOST (default: 0.0.0.0)
- PORT (default: 8001)
- STATIC_DIR (optional; serve UI files from this path)
- AUTH_FILE (default: ./auth.json)
- REQUIRE_AUTH (default: "true" if AUTH_FILE exists, otherwise "false")
- SUBFINDER_BIN (default: "subfinder")
- SUBFINDER_TIMEOUT (default: "45" seconds)
"""

import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import ssl
import os
import mimetypes
import subprocess
import shutil
import threading
import time
from datetime import datetime, timezone, timedelta

# New imports for metadata fetching with httpx
import re
import html
import asyncio
from typing import List, Dict, Any, Optional, Tuple

try:
    import httpx  # Ensure dependency installed: pip install httpx
except ImportError:
    httpx = None

# ---------- Utilities ----------
ISO = "%Y-%m-%dT%H:%M:%SZ"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO)


def parse_iso(ts: str) -> datetime:
    return datetime.strptime(ts, ISO).replace(tzinfo=timezone.utc)


def load_json(path: str, default):
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load JSON from {path}: {e}")
    return default


def save_json(path: str, data) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------- Auth Manager ----------
class AuthManager:
    def __init__(self):
        self.auth_file = os.environ.get("AUTH_FILE", os.path.abspath("auth.json"))
        self.config = load_json(self.auth_file, {})
        self.require_auth = self._should_require_auth()

    def _should_require_auth(self) -> bool:
        env = os.environ.get("REQUIRE_AUTH")
        if env is not None:
            return env.strip().lower() in ("1", "true", "yes", "on")
        # If an auth file exists with credentials, enforce auth by default.
        return bool(self.config.get("username") and self.config.get("password"))

    def check_basic(self, header_value: Optional[str]) -> bool:
        if not self.require_auth:
            return True
        if not header_value or not header_value.startswith("Basic "):
            return False
        try:
            import base64
            decoded = base64.b64decode(header_value.split(" ", 1)[1]).decode("utf-8", "ignore")
            # Format: username:password
            if ":" not in decoded:
                return False
            u, p = decoded.split(":", 1)
            return (u == self.config.get("username")) and (p == self.config.get("password"))
        except Exception:
            return False


# ---------- Monitor Manager ----------
class MonitorManager:
    def __init__(self, handler_cls_ref):
        # Monitors persisted on disk
        self.file_path = os.path.abspath("monitors.json")
        self.state = load_json(self.file_path, {"monitors": {}})
        # Recent in-memory events for /api/monitor/updates polling
        self.recent_events: List[Dict[str, Any]] = []
        self.recent_lock = threading.Lock()
        # Reference to handler class for calling shared fetch functions
        self.handler_cls = handler_cls_ref
        # Thread control
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._runner, daemon=True)
        self.thread.start()

    def list_monitors(self) -> Dict[str, Any]:
        return self.state.get("monitors", {})

    def get_monitor(self, domain: str) -> Optional[Dict[str, Any]]:
        return self.state.get("monitors", {}).get(domain)

    def set_monitor(self, domain: str, enabled: bool, interval_hours: Optional[int] = None) -> Dict[str, Any]:
        domain = domain.strip().lower()
        m = self.state.setdefault("monitors", {}).get(domain, {
            "enabled": False,
            "interval_hours": 12,
            "last_run": None,
            "last_results": [],
            "last_new": [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        m["enabled"] = bool(enabled)
        if interval_hours is not None:
            try:
                ih = int(interval_hours)
                if ih <= 0:
                    ih = 12
                m["interval_hours"] = ih
            except Exception:
                pass
        m["updated_at"] = now_iso()
        self.state["monitors"][domain] = m
        save_json(self.file_path, self.state)
        return m

    def delete_monitor(self, domain: str) -> bool:
        domain = domain.strip().lower()
        monitors = self.state.get("monitors", {})
        if domain in monitors:
            del monitors[domain]
            save_json(self.file_path, self.state)
            return True
        return False

    def add_event(self, domain: str, new_assets: List[str]) -> None:
        evt = {
            "type": "new_assets",
            "domain": domain,
            "count": len(new_assets),
            "new_subdomains": new_assets,
            "timestamp": now_iso(),
        }
        with self.recent_lock:
            self.recent_events.append(evt)
            # Keep last 200 events
            if len(self.recent_events) > 200:
                self.recent_events = self.recent_events[-200:]

    def get_events_since(self, since_iso: Optional[str]) -> List[Dict[str, Any]]:
        with self.recent_lock:
            if not since_iso:
                return list(self.recent_events)
            try:
                since_dt = parse_iso(since_iso)
            except Exception:
                return list(self.recent_events)
            out = []
            for e in self.recent_events:
                try:
                    if parse_iso(e.get("timestamp", "")) > since_dt:
                        out.append(e)
                except Exception:
                    out.append(e)
            return out

    def _runner(self):
        # Background scheduler loop
        print("Monitor thread started (12h default interval).")
        while not self.stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                print(f"Monitor tick error: {e}")
            # Wake up every 5 minutes to check if any monitor is due
            self.stop_event.wait(300.0)

    def _tick(self):
        monitors = self.state.get("monitors", {})
        if not monitors:
            return
        for domain, m in list(monitors.items()):
            if not m.get("enabled"):
                continue
            interval_hours = int(m.get("interval_hours", 12) or 12)
            last_run = m.get("last_run")
            due = False
            if not last_run:
                due = True
            else:
                try:
                    last_dt = parse_iso(last_run)
                    if datetime.now(timezone.utc) - last_dt >= timedelta(hours=interval_hours):
                        due = True
                except Exception:
                    due = True
            if not due:
                continue

            print(f"[monitor] Running scheduled scan for {domain}")
            # Perform a scan using the same logic as API sources
            all_subs = self._scan_domain(domain)
            prev = set(m.get("last_results") or [])
            found = set(all_subs)
            new_assets = sorted(found - prev)

            m["last_run"] = now_iso()
            m["last_results"] = sorted(found)
            m["last_new"] = new_assets
            m["updated_at"] = now_iso()
            self.state["monitors"][domain] = m
            save_json(self.file_path, self.state)

            if new_assets:
                print(f"[monitor] {domain}: {len(new_assets)} new assets")
                self.add_event(domain, new_assets)

    def _scan_domain(self, domain: str) -> List[str]:
        # Use handler class helpers (static functions below)
        crt = SubdomainAPIHandler.fetch_crt_subdomains(domain)
        wb = SubdomainAPIHandler.fetch_wayback_subdomains(domain)
        sf = SubdomainAPIHandler.run_subfinder(domain)
        merged = sorted(set(crt) | set(wb) | set(sf))
        return merged

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3.0)


# ---------- HTTP Handler ----------
class SubdomainAPIHandler(BaseHTTPRequestHandler):
    auth_manager = AuthManager()
    monitor_mgr = MonitorManager(handler_cls_ref=None)  # set later after class definition

    # ------------- Request entry points -------------
    def do_OPTIONS(self):
        # CORS preflight; don't enforce auth to allow browsers to send credentials later
        self.send_response(200)
        self._cors()
        self._std_headers()
        self.end_headers()

    def do_GET(self):
        if not self._enforce_auth():
            return
        parsed_path = urlparse(self.path)

        # API endpoints
        if parsed_path.path == '/api/crt':
            return self.handle_crt_api(parsed_path)
        if parsed_path.path == '/api/wayback':
            return self.handle_wayback_api(parsed_path)
        if parsed_path.path == '/api/subfinder':
            return self.handle_subfinder_api(parsed_path)
        if parsed_path.path == '/api/monitor':
            return self.handle_monitor_get(parsed_path)
        if parsed_path.path == '/api/monitor/updates':
            return self.handle_monitor_updates_get(parsed_path)

        # Static files (if configured)
        static_dir = os.environ.get('STATIC_DIR')
        if static_dir and os.path.isdir(static_dir):
            return self.handle_static_file(parsed_path, static_dir)

        self.send_error(404, "Not found")

    def do_POST(self):
        if not self._enforce_auth():
            return
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/meta':
            return self.handle_meta_api()
        if parsed_path.path == '/api/monitor':
            return self.handle_monitor_post()
        self.send_response(404)
        self._cors()
        self._std_headers()
        self.end_headers()
        self.wfile.write(b'{"error":"API endpoint not found"}')

    def do_DELETE(self):
        if not self._enforce_auth():
            return
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/monitor':
            return self.handle_monitor_delete(parsed_path)
        self.send_error(404, "Not found")

    # ------------- Auth/CORS/Headers helpers -------------
    def _enforce_auth(self) -> bool:
        # Exempt OPTIONS
        if self.command == "OPTIONS":
            return True
        ok = self.auth_manager.check_basic(self.headers.get("Authorization"))
        if ok:
            return True
        # Challenge
        self.send_response(401)
        self._cors()
        self.send_header("WWW-Authenticate", 'Basic realm="ASM"')
        self._std_headers()
        self.end_headers()
        self.wfile.write(b'{"error":"Unauthorized"}')
        return False

    def _cors(self):
        # Same-origin recommended; keep * for simplicity during development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def _std_headers(self):
        self.send_header('Cache-Control', 'no-store')

    # ------------- Static files -------------
    def handle_static_file(self, parsed_path, static_dir):
        try:
            file_path = parsed_path.path.lstrip('/')
            if not file_path or file_path == '/':
                file_path = 'index.html'
            full_path = os.path.join(static_dir, file_path)
            # Security check
            if not os.path.abspath(full_path).startswith(os.path.abspath(static_dir)):
                self.send_error(403, "Access denied")
                return
            if os.path.isfile(full_path):
                content_type, _ = mimetypes.guess_type(full_path)
                if not content_type:
                    content_type = 'application/octet-stream'
                with open(full_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self._cors()
                self._std_headers()
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")
        except Exception as e:
            print(f"Error serving static file: {e}")
            self.send_error(500, f"Error serving file: {str(e)}")

    # ------------- Subdomain sources -------------
    def handle_crt_api(self, parsed_path):
        try:
            query_params = parse_qs(parsed_path.query)
            domain = (query_params.get('domain', [None])[0] or "").strip().lower()
            if not domain:
                self.send_error(400, "Missing domain parameter")
                return

            data = self.fetch_crt_raw(domain)
            # pass-through raw JSON from crt.sh (array)
            self.send_response(200)
            self._cors()
            self._std_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            print(f"Error in crt handler: {e}")
            self.send_error(500, f"Error: {str(e)}")

    @staticmethod
    def fetch_crt_raw(domain: str) -> bytes:
        crt_url = f"https://crt.sh/?q=%.{domain}&output=json"
        try:
            ssl_context = ssl.create_default_context()
            with urllib.request.urlopen(crt_url, context=ssl_context) as response:
                return response.read()
        except Exception as api_error:
            print(f"Error calling crt.sh API: {api_error}")
            return json.dumps([]).encode('utf-8')

    @staticmethod
    def fetch_crt_subdomains(domain: str) -> List[str]:
        raw = SubdomainAPIHandler.fetch_crt_raw(domain)
        try:
            data = json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            data = []
        subs = set()
        for cert in data:
            try:
                names = (cert.get("name_value") or "").split("\n")
                for name in names:
                    n = name.strip().lower()
                    if n and (n == domain or n.endswith("." + domain)):
                        subs.add(n)
            except Exception:
                continue
        return sorted(subs)

    def handle_wayback_api(self, parsed_path):
        try:
            query_params = parse_qs(parsed_path.query)
            domain = (query_params.get('domain', [None])[0] or "").strip().lower()
            if not domain:
                self.send_error(400, "Missing domain parameter")
                return
            subs = self.fetch_wayback_subdomains(domain)
            payload = json.dumps(subs).encode('utf-8')
            self.send_response(200)
            self._cors()
            self._std_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:
            print(f"Error in Wayback handler: {e}")
            self.send_error(500, f"Error: {str(e)}")

    @staticmethod
    def fetch_wayback_subdomains(domain: str) -> List[str]:
        url = ("https://web.archive.org/cdx/search/cdx"
               f"?url=*.{domain}&fl=original&collapse=urlkey")
        try:
            ssl_context = ssl.create_default_context()
            with urllib.request.urlopen(url, context=ssl_context) as response:
                raw = response.read().decode('utf-8', errors='ignore')
        except Exception as api_error:
            print(f"Error calling Wayback CDX API: {api_error}")
            raw = ""
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        hosts = set()
        for line in lines:
            try:
                parsed = urlparse(line if '://' in line else 'http://' + line)
                host = parsed.netloc.split('@')[-1].split(':')[0].lower()
                if host and (host == domain or host.endswith("." + domain)):
                    hosts.add(host)
            except Exception:
                continue
        return sorted(hosts)

    def handle_subfinder_api(self, parsed_path):
        try:
            query_params = parse_qs(parsed_path.query)
            domain = (query_params.get('domain', [None])[0] or "").strip().lower()
            if not domain:
                self.send_error(400, "Missing domain parameter")
                return
            result = self.run_subfinder(domain)
            payload = json.dumps(result).encode('utf-8')
            self.send_response(200)
            self._cors()
            self._std_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:
            print(f"Error in Subfinder handler: {e}")
            self.send_error(500, f"Error: {str(e)}")

    @staticmethod
    def run_subfinder(domain: str) -> List[str]:
        subfinder_bin = os.environ.get('SUBFINDER_BIN', 'subfinder')
        if not shutil.which(subfinder_bin):
            # Tool not installed
            return []
        try:
            proc = subprocess.run(
                [subfinder_bin, '-silent', '-d', domain],
                capture_output=True,
                text=True,
                timeout=int(os.environ.get('SUBFINDER_TIMEOUT', '45'))
            )
            if proc.returncode != 0:
                print(f"Subfinder exited with {proc.returncode}: {proc.stderr.strip()}")
            lines = [ln.strip().lower() for ln in proc.stdout.splitlines() if ln.strip()]
            out, seen = [], set()
            for h in lines:
                host = h.split('@')[-1].split(':')[0]
                if host and (host == domain or host.endswith("." + domain)):
                    if host not in seen:
                        seen.add(host)
                        out.append(host)
            return sorted(out)
        except subprocess.TimeoutExpired:
            print("Subfinder timed out.")
            return []
        except Exception as e:
            print(f"Error running subfinder: {e}")
            return []

    # ------------- Monitor endpoints -------------
    def handle_monitor_get(self, parsed_path):
        params = parse_qs(parsed_path.query)
        domain = (params.get("domain", [None])[0] or "").strip().lower()
        self.send_response(200)
        self._cors()
        self._std_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        if domain:
            m = self.monitor_mgr.get_monitor(domain) or {}
            self.wfile.write(json.dumps(m).encode("utf-8"))
        else:
            self.wfile.write(json.dumps({"monitors": self.monitor_mgr.list_monitors()}).encode("utf-8"))

    def handle_monitor_post(self):
        try:
            length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(length) if length > 0 else b'{}'
            payload = json.loads(body.decode('utf-8') or '{}')
        except Exception:
            self.send_error(400, "Invalid JSON")
            return
        domain = (payload.get("domain") or "").strip().lower()
        enabled = bool(payload.get("enabled", True))
        interval_hours = payload.get("interval_hours")
        if not domain:
            self.send_error(400, "Missing domain")
            return
        # Basic domain validation (same regex as frontend roughly)
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.([a-zA-Z]{2,}|[a-zA-Z]{2,}\.[a-zA-Z]{2,})$", domain):
            self.send_error(400, "Invalid domain")
            return
        m = self.monitor_mgr.set_monitor(domain, enabled, interval_hours)
        self.send_response(200)
        self._cors()
        self._std_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(m).encode("utf-8"))

    def handle_monitor_delete(self, parsed_path):
        params = parse_qs(parsed_path.query)
        domain = (params.get("domain", [None])[0] or "").strip().lower()
        if not domain:
            self.send_error(400, "Missing domain")
            return
        ok = self.monitor_mgr.delete_monitor(domain)
        self.send_response(200 if ok else 404)
        self._cors()
        self._std_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"deleted": bool(ok)}).encode("utf-8"))

    def handle_monitor_updates_get(self, parsed_path):
        params = parse_qs(parsed_path.query)
        since = (params.get("since", [None])[0] or "").strip() or None
        events = self.monitor_mgr.get_events_since(since)
        payload = {
            "server_time": now_iso(),
            "events": events
        }
        self.send_response(200)
        self._cors()
        self._std_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    # ------------- Metadata endpoint -------------
    def handle_meta_api(self):
        if httpx is None:
            self.send_response(500)
            self._cors()
            self._std_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":"httpx is not installed on server"}')
            return

        try:
            length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(length) if length > 0 else b'{}'
            payload = json.loads(body.decode('utf-8') or '{}')
        except Exception as e:
            self.send_response(400)
            self._cors()
            self._std_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON payload: {e}"}).encode('utf-8'))
            return

        hosts = payload.get('hosts', [])
        timeout_ms = payload.get('timeout_ms', 4000)

        if not isinstance(hosts, list) or not hosts:
            self.send_response(400)
            self._cors()
            self._std_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":"Provide a non-empty hosts array"}')
            return

        if len(hosts) > 200:
            self.send_response(400)
            self._cors()
            self._std_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error":"Too many hosts; max 200 per request"}')
            return

        # Normalize and deduplicate
        ordered_hosts = []
        seen = set()
        for h in hosts:
            if isinstance(h, str):
                h = h.strip().lower()
            if not h or h in seen:
                continue
            seen.add(h)
            ordered_hosts.append(h)

        try:
            timeout = max(1.0, float(timeout_ms) / 1000.0)
        except Exception:
            timeout = 4.0

        try:
            results = asyncio.run(fetch_metadata_for_hosts(ordered_hosts, timeout))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(fetch_metadata_for_hosts(ordered_hosts, timeout))
            loop.close()

        # Preserve original order
        order_index = {h: i for i, h in enumerate(ordered_hosts)}
        results.sort(key=lambda r: order_index.get(r.get('host', ''), 10**9))

        data = json.dumps(results).encode('utf-8')
        self.send_response(200)
        self._cors()
        self._std_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


# ---------- Helpers for /api/meta ----------
TITLE_RE = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)

def extract_title_from_html(html_text: str) -> str:
    try:
        m = TITLE_RE.search(html_text or '')
        if not m:
            return ''
        title = m.group(1)
        title = re.sub(r'\s+', ' ', title).strip()
        return html.unescape(title)
    except Exception:
        return ''

async def fetch_one_host(host: str, timeout: float) -> Dict[str, Any]:
    headers = {
        "User-Agent": "ASM-Scanner/1.0 (+https://github.com/iamnoone1337/ASM)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "close",
    }
    schemes = ["https", "http"]
    error_msg = "Unknown error"

    async with httpx.AsyncClient(follow_redirects=True, headers=headers, timeout=timeout, verify=True) as client:
        for scheme in schemes:
            url = f"{scheme}://{host}"
            start = time.time()
            try:
                resp = await client.get(url)
                status = resp.status_code
                content_type = resp.headers.get('content-type', '')
                title = ''
                if isinstance(content_type, str) and 'text/html' in content_type.lower():
                    text = resp.text
                    if len(text) > 200000:
                        text = text[:200000]
                    title = extract_title_from_html(text)

                return {
                    "host": host,
                    "url": url,
                    "scheme": scheme,
                    "status_code": int(status),
                    "title": title,
                    "checked_at": datetime.utcnow().strftime(ISO),
                    "elapsed_ms": int((time.time() - start) * 1000),
                    "error": ""
                }
            except httpx.RequestError as e:
                error_msg = str(e)
            except Exception as e:
                error_msg = str(e)

    return {
        "host": host,
        "url": "",
        "scheme": "",
        "status_code": None,
        "title": "",
        "checked_at": datetime.utcnow().strftime(ISO),
        "elapsed_ms": None,
        "error": error_msg
    }

async def fetch_metadata_for_hosts(hosts: List[str], timeout: float) -> List[Dict[str, Any]]:
    tasks = [fetch_one_host(h, timeout) for h in hosts]
    return await asyncio.gather(*tasks)


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8001'))
    static_dir = os.environ.get('STATIC_DIR')

    httpd = ThreadingHTTPServer((host, port), SubdomainAPIHandler)
    # Attach the handler class to monitor manager if needed
    SubdomainAPIHandler.monitor_mgr.handler_cls = SubdomainAPIHandler

    print(f"Subdomain enumeration server running on http://{host}:{port}")
    print("Auth:", "ENABLED" if SubdomainAPIHandler.auth_manager.require_auth else "DISABLED")
    if SubdomainAPIHandler.auth_manager.require_auth:
        print(f"  - Using credentials from: {SubdomainAPIHandler.auth_manager.auth_file}")
    print("API Endpoints:")
    print("  - GET  /api/crt?domain=example.com")
    print("  - GET  /api/wayback?domain=example.com")
    print("  - GET  /api/subfinder?domain=example.com   (requires subfinder installed)")
    print('  - POST /api/meta   ({"hosts":["a.example.com"], "timeout_ms":4000})')
    print('  - GET  /api/monitor                              (list all)')
    print('  - GET  /api/monitor?domain=example.com           (get one)')
    print('  - POST /api/monitor   {"domain":"example.com", "enabled":true, "interval_hours":12}')
    print('  - DELETE /api/monitor?domain=example.com')
    print('  - GET  /api/monitor/updates?since=YYYY-MM-DDTHH:MM:SSZ')
    if static_dir:
        if os.path.isdir(static_dir):
            print(f"Static files served from: {static_dir}")
            print(f"  - Web interface available at http://{host}:{port}/")
        else:
            print(f"Warning: STATIC_DIR '{static_dir}' does not exist or is not a directory")
    else:
        print("Static file serving disabled (set STATIC_DIR to enable)")

    print("\nSources used:")
    print("  - https://crt.sh/?q=%.DOMAIN&output=json")
    print("  - https://web.archive.org/cdx/search/cdx?url=*.DOMAIN&fl=original&collapse=urlkey")
    print("  - subfinder -silent -d DOMAIN (optional)")
    print("  - http(s)://<subdomain> for status/title via httpx")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        SubdomainAPIHandler.monitor_mgr.stop()
        httpd.server_close()
