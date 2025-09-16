# Subdomain Enumerator

A beautiful and modern web application that discovers subdomains for any given domain using Certificate Transparency logs from crt.sh and Web Archive.

## Features

- **Modern UI**: Clean, responsive design with glassmorphism effects
- **Real-time Search**: Instant subdomain enumeration using crt.sh API and Web Archive
- **Interactive Results**: 
  - Filter subdomains by name
  - Copy subdomains to clipboard
  - Visit subdomains directly
  - Export results to text file
- **Loading States**: Smooth loading animations and progress indicators
- **Error Handling**: Comprehensive error messages and retry functionality
- **Mobile Responsive**: Works perfectly on all device sizes
- **CORS Solution**: Server-side API processing eliminates browser CORS restrictions

## How to Use

### Setup
1. Start the backend server: `python3 server.py` (listens on http://127.0.0.1:8001)
2. Start the web server: `python3 -m http.server 8000`
3. Open `http://localhost:8000` in your browser

**Important**: All external requests to crt.sh and Web Archive are made server-side by the backend to avoid CORS issues. The browser never calls those origins directly.

### Usage
1. Enter a domain name (e.g., `hackerone.com`) in the input field
2. Click "Enumerate" or press Enter
3. Wait for the results to load
4. Use the filter to search through results
5. Copy individual subdomains or export all results

## Technical Details

- **Frontend**: Pure HTML, CSS, and JavaScript (no frameworks required)
- **Backend API Endpoints**:
  - `GET /api/crt?domain={domain}` - Server-side calls to https://crt.sh/?q=%.{domain}&output=json
  - `GET /api/webarchive?domain={domain}` - Server-side calls to https://web.archive.org/cdx/search/cdx?url=*.{domain}&fl=original&collapse=urlkey
- **Server-side Processing**: Backend parses and filters subdomain results before sending to frontend
- **CORS Solution**: All external API calls are made server-side to avoid browser CORS restrictions
- **Styling**: Modern CSS with gradients, glassmorphism, and smooth animations
- **Icons**: Font Awesome icons for better UX
- **Fonts**: Inter font family for clean typography

## Files

- `index.html` - Main HTML structure
- `styles.css` - CSS styling and responsive design
- `script.js` - JavaScript functionality and API integration
- `server.py` - Backend server for server-side API calls to external services
- `RUNNING.md` - Detailed setup and running instructions

## Browser Compatibility

Works in all modern browsers that support:
- ES6+ JavaScript features
- CSS Grid and Flexbox
- Fetch API
- CSS Custom Properties

## Privacy

This tool only queries public Certificate Transparency logs and doesn't store any data locally or on any servers.