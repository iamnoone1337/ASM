#!/usr/bin/env python3
"""
Backend server for subdomain enumeration
- crt.sh via /api/crt
- Wayback Machine (CDX) via /api/wayback
- Subfinder via /api/subfinder
- HTTP metadata (status/title) via /api/meta
"""
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import ssl
import os
import mimetypes
import subprocess
import shutil

# New imports for metadata fetching with httpx
import re
import html
import asyncio
import time
from typing import List, Dict, Any

try:
    import httpx  # Ensure dependency installed: pip install httpx
except ImportError:
    httpx = None

class SubdomainAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests for API endpoints and static files"""
        parsed_path = urlparse(self.path)

        # Handle API endpoints
        if parsed_path.path == '/api/crt':
            self.handle_crt_api(parsed_path)
        elif parsed_path.path == '/api/wayback':
            self.handle_wayback_api(parsed_path)
        elif parsed_path.path == '/api/subfinder':
            self.handle_subfinder_api(parsed_path)
        else:
            # Handle static file serving if STATIC_DIR is configured
            static_dir = os.environ.get('STATIC_DIR')
            if static_dir and os.path.isdir(static_dir):
                self.handle_static_file(parsed_path, static_dir)
            else:
                self.send_error(404, "API endpoint not found")

    def do_POST(self):
        """Handle POST APIs"""
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/meta':
            self.handle_meta_api()
        else:
            self.send_response(404)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"error":"API endpoint not found"}')

    def handle_static_file(self, parsed_path, static_dir):
        """Handle static file requests"""
        try:
            # Remove leading slash and handle root path
            file_path = parsed_path.path.lstrip('/')
            if not file_path or file_path == '/':
                file_path = 'index.html'

            full_path = os.path.join(static_dir, file_path)

            # Security check - ensure we're not serving files outside static_dir
            if not os.path.abspath(full_path).startswith(os.path.abspath(static_dir)):
                self.send_error(403, "Access denied")
                return

            if os.path.isfile(full_path):
                # Determine content type
                content_type, _ = mimetypes.guess_type(full_path)
                if not content_type:
                    content_type = 'application/octet-stream'

                # Read and serve file
                with open(full_path, 'rb') as f:
                    content = f.read()

                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
                # Add CORS headers for development flexibility
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")

        except Exception as e:
            print(f"Error serving static file: {e}")
            self.send_error(500, f"Error serving file: {str(e)}")

    def handle_crt_api(self, parsed_path):
        """Handle crt.sh API requests - server-side call"""
        try:
            # Extract domain from query parameters
            query_params = parse_qs(parsed_path.query)
            domain = query_params.get('domain', [None])[0]

            if not domain:
                self.send_error(400, "Missing domain parameter")
                return

            # Make server-side API call to crt.sh
            crt_url = f"https://crt.sh/?q=%.{domain}&output=json"

            try:
                # Create SSL context for secure connection
                ssl_context = ssl.create_default_context()

                with urllib.request.urlopen(crt_url, context=ssl_context) as response:
                    data = response.read()

                # Send response with CORS headers
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)

            except Exception as api_error:
                print(f"Error calling crt.sh API: {api_error}")
                # Return empty array if API call fails
                empty_response = json.dumps([]).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(empty_response)

        except Exception as e:
            print(f"Error in crt.sh API handler: {e}")
            self.send_error(500, f"Error fetching from crt.sh: {str(e)}")

    def handle_wayback_api(self, parsed_path):
        """Handle Wayback CDX API requests - server-side call for subdomains."""
        try:
            query_params = parse_qs(parsed_path.query)
            domain = query_params.get('domain', [None])[0]
            if not domain:
                self.send_error(400, "Missing domain parameter")
                return

            # Wayback CDX API request
            # Example: https://web.archive.org/cdx/search/cdx?url=*.techgig.com&fl=original&collapse=urlkey
            wb_url = (
                "https://web.archive.org/cdx/search/cdx"
                f"?url=*.{domain}&fl=original&collapse=urlkey"
            )

            try:
                ssl_context = ssl.create_default_context()
                with urllib.request.urlopen(wb_url, context=ssl_context) as response:
                    raw = response.read().decode('utf-8', errors='ignore')
            except Exception as api_error:
                print(f"Error calling Wayback CDX API: {api_error}")
                raw = ""

            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            subdomains = self.extract_subdomains_from_wayback_lines(domain.lower(), lines)
            payload = json.dumps(sorted(subdomains)).encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(payload)

        except Exception as e:
            print(f"Error in Wayback API handler: {e}")
            self.send_error(500, f"Error fetching from Wayback: {str(e)}")

    def extract_subdomains_from_wayback_lines(self, domain: str, lines: List[str]) -> List[str]:
        """Parse original URLs from Wayback CDX into unique hostnames under the given domain."""
        hosts = set()
        for line in lines:
            try:
                parsed = urlparse(line if '://' in line else 'http://' + line)
                host = parsed.netloc.split('@')[-1].split(':')[0].lower()
                if not host:
                    continue
                if host == domain or host.endswith('.' + domain):
                    hosts.add(host)
            except Exception:
                continue
        return list(hosts)

    def handle_subfinder_api(self, parsed_path):
        """Handle Subfinder enumeration - server-side execution."""
        try:
            query_params = parse_qs(parsed_path.query)
            domain = query_params.get('domain', [None])[0]
            if not domain:
                self.send_error(400, "Missing domain parameter")
                return

            subfinder_bin = os.environ.get('SUBFINDER_BIN', 'subfinder')
            if not shutil.which(subfinder_bin):
                print("Subfinder not found on PATH; returning empty result.")
                result = []
            else:
                # Run subfinder -silent -d domain
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
                    # Keep hosts that belong to the domain
                    result = []
                    seen = set()
                    for h in lines:
                        # Ensure it's a hostname (basic validation)
                        host = h.split('@')[-1].split(':')[0]
                        if host and (host == domain.lower() or host.endswith('.' + domain.lower())):
                            if host not in seen:
                                seen.add(host)
                                result.append(host)
                except subprocess.TimeoutExpired:
                    print("Subfinder timed out.")
                    result = []
                except Exception as e:
                    print(f"Error running subfinder: {e}")
                    result = []

            payload = json.dumps(sorted(result)).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(payload)

        except Exception as e:
            print(f"Error in Subfinder API handler: {e}")
            self.send_error(500, f"Error running subfinder: {str(e)}")

    # ---------- /api/meta to fetch status code + title via httpx ----------

    def handle_meta_api(self):
        """Handle POST /api/meta for fetching status codes and titles."""
        if httpx is None:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"error":"httpx is not installed on server"}')
            return

        try:
            length = int(self.headers.get('Content-Length') or 0)
            body = self.rfile.read(length) if length > 0 else b'{}'
            payload = json.loads(body.decode('utf-8') or '{}')
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Invalid JSON payload: {e}"}).encode('utf-8'))
            return

        hosts = payload.get('hosts', [])
        timeout_ms = payload.get('timeout_ms', 4000)

        if not isinstance(hosts, list) or not hosts:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"error":"Provide a non-empty hosts array"}')
            return

        if len(hosts) > 200:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
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

        # Run async metadata fetch
        try:
            results = asyncio.run(fetch_metadata_for_hosts(ordered_hosts, timeout))
        except RuntimeError:
            # Create a new loop manually if one is already running.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(fetch_metadata_for_hosts(ordered_hosts, timeout))
            loop.close()

        # Preserve original order
        order_index = {h: i for i, h in enumerate(ordered_hosts)}
        results.sort(key=lambda r: order_index.get(r.get('host', ''), 10**9))

        data = json.dumps(results).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
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
                    "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_ms": None,
        "error": error_msg
    }

async def fetch_metadata_for_hosts(hosts: List[str], timeout: float) -> List[Dict[str, Any]]:
    tasks = [fetch_one_host(h, timeout) for h in hosts]
    return await asyncio.gather(*tasks)

if __name__ == '__main__':
    # Get configuration from environment variables
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8001'))
    static_dir = os.environ.get('STATIC_DIR')

    server = HTTPServer((host, port), SubdomainAPIHandler)

    print(f"Subdomain enumeration server running on http://{host}:{port}")
    print("API Endpoints:")
    print("  - GET  /api/crt?domain=example.com")
    print("  - GET  /api/wayback?domain=example.com")
    print("  - GET  /api/subfinder?domain=example.com")
    print('  - POST /api/meta   ({"hosts":["a.example.com"], "timeout_ms":4000})')

    if static_dir:
        if os.path.isdir(static_dir):
            print(f"Static files served from: {static_dir}")
            print(f"  - Web interface available at http://{host}:{port}/")
        else:
            print(f"Warning: STATIC_DIR '{static_dir}' does not exist or is not a directory")
    else:
        print("Static file serving disabled (set STATIC_DIR to enable)")

    print("\nServer-side API calls to:")
    print("  - https://crt.sh/?q=%.DOMAIN&output=json")
    print("  - https://web.archive.org/cdx/search/cdx?url=*.DOMAIN&fl=original&collapse=urlkey")
    print("  - subfinder -silent -d DOMAIN (requires Subfinder installed)")
    print("  - http(s)://<subdomain> for status/title via httpx")
    print(f"\nEnvironment variables:")
    print(f"  HOST={host} (default: 0.0.0.0)")
    print(f"  PORT={port} (default: 8001)")
    print(f"  STATIC_DIR={static_dir or 'not set'} (optional)")
    print(f"  SUBFINDER_BIN={os.environ.get('SUBFINDER_BIN', 'subfinder')} (optional)")
    print(f"  SUBFINDER_TIMEOUT={os.environ.get('SUBFINDER_TIMEOUT', '45')}s (optional)")

    server.serve_forever()
