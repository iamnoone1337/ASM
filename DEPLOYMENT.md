# VPS Deployment Guide

This guide explains how to deploy the Subdomain Enumerator on a VPS (Virtual Private Server) for production use.

## Overview

The application consists of:
- **Frontend**: Static HTML, CSS, and JavaScript files
- **Backend**: Python server that provides API endpoints for crt.sh and Web Archive

The frontend uses same-origin API calls by default, eliminating CORS issues in production.

## Deployment Options

### Option A: Single-Process Mode (Simple)

Run the Python server with both API and static file serving:

```bash
# Set environment variables
export HOST=0.0.0.0
export PORT=8001
export STATIC_DIR=/path/to/subdomain-enumerator

# Run the server
python3 server.py
```

Access your application at `http://YOUR_VPS_IP:8001`

**Environment Variables:**
- `HOST`: Server bind address (default: `0.0.0.0`)
- `PORT`: Server port (default: `8001`)
- `STATIC_DIR`: Path to static files directory (optional, enables static serving)

### Option B: Nginx Reverse Proxy (Recommended)

This setup uses Nginx to serve static files and reverse proxy API requests to the Python backend.

#### 1. Install Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx python3 python3-pip certbot python3-certbot-nginx

# Clone the repository
git clone https://github.com/iamnoone1337/ASM.git
cd ASM
```

#### 2. Configure Nginx

Create `/etc/nginx/sites-available/subdomain-enumerator`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Serve static files
    location / {
        root /path/to/ASM;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Reverse proxy API requests to Python backend
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (optional, for development)
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/subdomain-enumerator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 3. Set Up Python Backend Service

Create systemd service file `/etc/systemd/system/subdomain-api.service`:

```ini
[Unit]
Description=Subdomain Enumerator API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/ASM
Environment=HOST=127.0.0.1
Environment=PORT=8001
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable subdomain-api
sudo systemctl start subdomain-api
sudo systemctl status subdomain-api
```

#### 4. Enable HTTPS (Recommended)

```bash
# Get SSL certificate via Let's Encrypt
sudo certbot --nginx -d your-domain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

## Configuration Options

### Custom API Base URL

If you host the API on a different subdomain, add this meta tag to `index.html`:

```html
<meta name="api-base-url" content="https://api.yourdomain.com">
```

### Firewall Configuration

For single-process mode, open the required port:

```bash
# UFW (Ubuntu)
sudo ufw allow 8001

# iptables
sudo iptables -A INPUT -p tcp --dport 8001 -j ACCEPT
```

For Nginx setup, only HTTP/HTTPS ports are needed:

```bash
sudo ufw allow 'Nginx Full'
```

## Monitoring and Logs

### View Service Logs

```bash
# API server logs
sudo journalctl -u subdomain-api -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Health Check

Test API endpoints:

```bash
# Test crt.sh API
curl "https://your-domain.com/api/crt?domain=example.com"

# Test Web Archive API
curl "https://your-domain.com/api/webarchive?domain=example.com"
```

## Security Considerations

1. **Firewall**: Only open necessary ports (80, 443 for Nginx setup)
2. **Updates**: Keep system and dependencies updated
3. **Rate Limiting**: Consider adding rate limiting in Nginx for API endpoints
4. **Monitoring**: Set up monitoring for service health and resource usage

## Troubleshooting

### Common Issues

1. **API calls fail**: Check if backend service is running and accessible
2. **CORS errors**: Verify same-origin setup or meta tag configuration
3. **Static files not loading**: Check Nginx configuration and file permissions
4. **SSL issues**: Verify certificate installation and renewal

### Debug Commands

```bash
# Check if backend is responding
curl -I http://127.0.0.1:8001/api/crt?domain=test.com

# Check Nginx configuration
sudo nginx -t

# Test from different locations
curl -I https://your-domain.com/
curl -I https://your-domain.com/api/crt?domain=test.com
```

## Performance Optimization

1. **Enable Gzip**: Add gzip compression in Nginx
2. **CDN**: Use a CDN for static assets if needed
3. **Caching**: Implement API response caching if appropriate
4. **Resource Limits**: Set appropriate limits in systemd service

Example Nginx gzip configuration:

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
```

This setup provides a production-ready deployment with proper separation of concerns, security, and scalability.