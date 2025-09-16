#!/usr/bin/env python3
"""
Backend server for subdomain enumeration
Makes server-side API calls to avoid CORS issues
"""
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import ssl
import os
import mimetypes

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
        elif parsed_path.path == '/api/webarchive':
            self.handle_webarchive_api(parsed_path)
        else:
            # Handle static file serving if STATIC_DIR is configured
            static_dir = os.environ.get('STATIC_DIR')
            if static_dir and os.path.isdir(static_dir):
                self.handle_static_file(parsed_path, static_dir)
            else:
                self.send_error(404, "API endpoint not found")

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

    def handle_webarchive_api(self, parsed_path):
        """Handle Web Archive API requests - server-side call"""
        try:
            # Extract domain from query parameters
            query_params = parse_qs(parsed_path.query)
            domain = query_params.get('domain', [None])[0]
            
            if not domain:
                self.send_error(400, "Missing domain parameter")
                return
            
            # Make server-side API call to Web Archive using the specified URL format
            archive_url = f"https://web.archive.org/cdx/search/cdx?url=*.{domain}&fl=original&collapse=json"
            
            try:
                # Create SSL context for secure connection
                ssl_context = ssl.create_default_context()
                
                with urllib.request.urlopen(archive_url, context=ssl_context) as response:
                    data = response.read()
                    
                # Send response with CORS headers
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                
            except Exception as api_error:
                print(f"Error calling Web Archive API: {api_error}")
                # Return empty string if API call fails
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"")
                
        except Exception as e:
            print(f"Error in Web Archive API handler: {e}")
            self.send_error(500, f"Error fetching from Web Archive: {str(e)}")

if __name__ == '__main__':
    # Get configuration from environment variables
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8001'))
    static_dir = os.environ.get('STATIC_DIR')
    
    server = HTTPServer((host, port), SubdomainAPIHandler)
    
    print(f"Subdomain enumeration server running on http://{host}:{port}")
    print("API Endpoints:")
    print(f"  - GET /api/crt?domain=example.com")
    print(f"  - GET /api/webarchive?domain=example.com")
    
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
    print(f"\nEnvironment variables:")
    print(f"  HOST={host} (default: 0.0.0.0)")
    print(f"  PORT={port} (default: 8001)")
    print(f"  STATIC_DIR={static_dir or 'not set'} (optional)")
    
    server.serve_forever()
