#!/bin/sh

# Substitute environment variables in nginx config
envsubst '$BACKEND_PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Generate config.js with environment variables
cat > /usr/share/nginx/html/config.js <<EOF
window.ENV = {
    BACKEND_PORT: '${BACKEND_PORT:-8000}',
    API_URL: window.location.hostname === 'localhost' ? 'http://localhost:${BACKEND_PORT:-8000}' : ''
};
EOF

# Start nginx
nginx -g 'daemon off;'