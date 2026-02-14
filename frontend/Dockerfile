FROM nginx:alpine

# Install envsubst and wget
RUN apk add --no-cache gettext wget

# Copy static files
COPY . /usr/share/nginx/html

# Copy start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Create nginx config template with proper proxy settings
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    \
    location /api/ { \
        proxy_pass ${BACKEND_URL}/api/; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        proxy_read_timeout 86400; \
    } \
}' > /etc/nginx/conf.d/default.conf.template

EXPOSE 80

CMD ["/start.sh"]