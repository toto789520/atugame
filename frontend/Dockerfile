FROM nginx:alpine

# Copy static files
COPY . /usr/share/nginx/html

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create nginx config template (will be processed at runtime)
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

# Create nginx config with env substitution
RUN echo '#!/bin/sh \
    envsubst "$$BACKEND_PORT" < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf \
    /entrypoint.sh' > /start.sh && chmod +x /start.sh

EXPOSE 80

CMD ["/start.sh"]