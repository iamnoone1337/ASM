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

## How to Use

1. Open `index.html` in your web browser
2. Enter a domain name (e.g., `example.com`) in the input field
3. Click "Enumerate" or press Enter
4. Wait for the results to load
5. Use the filter to search through results
6. Copy individual subdomains or export all results

## Technical Details

- **Frontend**: Pure HTML, CSS, and JavaScript (no frameworks required)
- **API**: Uses crt.sh Certificate Transparency API
- **Styling**: Modern CSS with gradients, glassmorphism, and smooth animations
- **Icons**: Font Awesome icons for better UX
- **Fonts**: Inter font family for clean typography

## Files

- `index.html` - Main HTML structure
- `styles.css` - CSS styling and responsive design
- `script.js` - JavaScript functionality and API integration

## Browser Compatibility

Works in all modern browsers that support:
- ES6+ JavaScript features
- CSS Grid and Flexbox
- Fetch API
- CSS Custom Properties

## Privacy

This tool only queries public Certificate Transparency logs and doesn't store any data locally or on any servers.