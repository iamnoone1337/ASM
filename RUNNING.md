# Running the Subdomain Enumerator

This application uses a backend server to make server-side API calls to external services, avoiding CORS restrictions.

## Setup and Running

1. **Start the backend server:**
   ```bash
   python3 server.py
   ```
   This will start the backend server on `http://127.0.0.1:8001`

2. **Start the web server:**
   ```bash
   python3 -m http.server 8000
   ```
   This will serve the web application on `http://localhost:8000`

3. **Open the application:**
   Navigate to `http://localhost:8000` in your web browser

## API Endpoints

The backend server provides two main endpoints:

- `GET /api/crt?domain={domain}` - Queries crt.sh Certificate Transparency logs
- `GET /api/webarchive?domain={domain}` - Queries Web Archive CDX API

## Testing

Test the application with `hackerone.com` to see the subdomain enumeration in action. The application will return a list of discovered subdomains including:
- api.hackerone.com
- docs.hackerone.com
- support.hackerone.com
- www.hackerone.com
- And several others

## Architecture

The solution uses a backend server to:
- Make server-side API calls to crt.sh (https://crt.sh/?q=%.{domain}&output=json)
- Make server-side API calls to Web Archive CDX (https://web.archive.org/cdx/search/cdx?url=*.{domain}&fl=original&collapse=urlkey)
- Process and filter subdomain results server-side
- Avoid browser CORS restrictions by handling all external requests server-side  
- Return processed, filtered subdomain arrays to the frontend

**Important**: All external requests are made on the backend to avoid CORS. The browser never calls crt.sh or web.archive.org directly.