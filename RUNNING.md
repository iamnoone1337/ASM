# Running the Subdomain Enumerator

This application requires a proxy server to bypass CORS restrictions when making requests to external APIs.

## Setup and Running

1. **Start the proxy server:**
   ```bash
   python3 proxy_server.py
   ```
   This will start a CORS proxy server on `http://localhost:8001`

2. **Start the web server:**
   ```bash
   python3 -m http.server 8000
   ```
   This will serve the web application on `http://localhost:8000`

3. **Open the application:**
   Navigate to `http://localhost:8000` in your web browser

## Testing

Test the application with `hackerone.com` to see the subdomain enumeration in action. The application will return a list of discovered subdomains including:
- api.hackerone.com
- docs.hackerone.com
- support.hackerone.com
- www.hackerone.com
- And several others

## Architecture

The solution uses a local Python proxy server to:
- Bypass browser CORS restrictions
- Make requests to external APIs (crt.sh and web.archive.org)
- Return properly formatted responses to the frontend

This ensures the application can successfully enumerate subdomains without encountering CORS-related errors.