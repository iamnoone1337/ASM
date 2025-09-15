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

class SubdomainAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests for API endpoints"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/crt':
            self.handle_crt_api(parsed_path)
        elif parsed_path.path == '/api/webarchive':
            self.handle_webarchive_api(parsed_path)
        else:
            self.send_error(404, "API endpoint not found")

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
    port = 8001
    server = HTTPServer(('localhost', port), SubdomainAPIHandler)
    print(f"Subdomain enumeration backend server running on http://localhost:{port}")
    print("Endpoints:")
    print(f"  - GET /api/crt?domain=example.com")
    print(f"  - GET /api/webarchive?domain=example.com")
    print("\nServer-side API calls to:")
    print("  - https://crt.sh/?q=%.DOMAIN&output=json")
    print("  - https://web.archive.org/cdx/search/cdx?url=*.DOMAIN&fl=original&collapse=json")
    server.serve_forever()