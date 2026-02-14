FROM nginx:alpine

# Install envsubst
RUN apk add --no-cache gettext

# Copy static files
COPY . /usr/share/nginx/html

# Copy start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Create nginx config template
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://backend:${BACKEND_PORT}/api; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf.template

EXPOSE 80

CMD ["/start.sh"]