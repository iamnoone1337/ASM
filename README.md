# Subdomain Enumerator

A beautiful and modern web application that discovers subdomains for any given domain using Certificate Transparency logs from crt.sh.

## Features

- **Modern UI**: Clean, responsive design with glassmorphism effects
- **Real-time Search**: Instant subdomain enumeration using crt.sh API
- **Interactive Results**: 
  - Filter subdomains by name
  - Copy subdomains to clipboard
  - Visit subdomains directly
  - Export results to text file
- **Loading States**: Smooth loading animations and progress indicators
- **Error Handling**: Comprehensive error messages and retry functionality
- **Mobile Responsive**: Works perfectly on all device sizes
- **CORS Solution**: Includes proxy server to bypass browser restrictions

## How to Use

### Development Setup
For local development, see [RUNNING.md](RUNNING.md) for detailed instructions.

### Production Deployment
For VPS deployment, see [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive setup guides including:
- Single-process mode (simple setup)
- Nginx reverse proxy mode (recommended)
- SSL/TLS configuration
- Systemd service setup

### Usage
1. Enter a domain name (e.g., `hackerone.com`) in the input field
2. Click "Enumerate" or press Enter
3. Wait for the results to load
4. Use the filter to search through results
5. Copy individual subdomains or export all results

## Technical Details

- **Frontend**: Pure HTML, CSS, and JavaScript (no frameworks required)
- **APIs**: Uses crt.sh Certificate Transparency API
- **Backend Server**: Python backend that makes server-side API calls to avoid CORS issues
- **Styling**: Modern CSS with gradients, glassmorphism, and smooth animations
- **Icons**: Font Awesome icons for better UX
- **Fonts**: Inter font family for clean typography

## Files

- `index.html` - Main HTML structure
- `styles.css` - CSS styling and responsive design
- `script.js` - JavaScript functionality and API integration
- `server.py` - Backend server for server-side API calls to external services
- `RUNNING.md` - Development setup and running instructions
- `DEPLOYMENT.md` - Production deployment guide for VPS

## Browser Compatibility

Works in all modern browsers that support:
- ES6+ JavaScript features
- CSS Grid and Flexbox
- Fetch API
- CSS Custom Properties

## Privacy

This tool only queries public Certificate Transparency logs and doesn't store any data locally or on any servers.