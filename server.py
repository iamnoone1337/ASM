#!/usr/bin/env python3
"""
Backend server for subdomain enumeration
Makes server-side API calls to avoid CORS issues
"""
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import ssl
import os
import mimetypes

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
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
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
            query_params = parse_qs(parsed_path.query)
            domain = query_params.get('domain', [None])[0]
            
            if not domain:
                self.send_error(400, "Missing domain parameter")
                return
            
            crt_url = f"https://crt.sh/?q=%.{domain}&output=json"
            
            try:
                ssl_context = ssl.create_default_context()
                with urllib.request.urlopen(crt_url, context=ssl_context) as response:
                    data = response.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                
            except Exception as api_error:
                print(f"Error calling crt.sh API: {api_error}")
                empty_response = json.dumps([]).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(empty_response)
            
        except Exception as e:
            print(f"Error in crt.sh API handler: {e}")
            self.send_error(500, f"Error fetching from crt.sh: {str(e)}")

    # ---------- New: /api/meta to fetch status code + title via httpx ----------
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
            # If a loop is already running, create a new one
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
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8001'))
    static_dir = os.environ.get('STATIC_DIR')
    
    server = HTTPServer((host, port), SubdomainAPIHandler)
    
    print(f"Subdomain enumeration server running on http://{host}:{port}")
    print("API Endpoints:")
    print(f"  - GET  /api/crt?domain=example.com")
    print(f"  - POST /api/meta   ({\"hosts\":[\"a.example.com\"], \"timeout_ms\":4000})")
    
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
    print("  - http(s)://<subdomain> for status/title via httpx")
    print(f"\nEnvironment variables:")
    print(f"  HOST={host} (default: 0.0.0.0)")
    print(f"  PORT={port} (default: 8001)")
    print(f"  STATIC_DIR={static_dir or 'not set'} (optional)")
    
    server.serve_forever()
