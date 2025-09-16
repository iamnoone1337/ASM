# Running the Subdomain Enumerator

This application uses a backend server to make server-side API calls to external services, avoiding CORS restrictions.

## Setup and Running

1. **Start the backend server:**
   ```bash
   python3 server.py
   ```
   This will start the backend server on `http://localhost:8001`

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

The solution uses a backend server to:
- Make server-side API calls to external services (crt.sh)
- Avoid browser CORS restrictions by handling all external requests server-side  
- Return properly formatted responses to the frontend

This ensures the application can successfully enumerate subdomains without encountering CORS-related errors.