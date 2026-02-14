#!/bin/sh

echo "=== Starting Frontend Configuration ==="
echo "BACKEND_URL: ${BACKEND_URL:-http://backend:8000}"

# Substitute environment variables in nginx config
envsubst '$BACKEND_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "=== Nginx Config Generated ==="
cat /etc/nginx/conf.d/default.conf

# Always use relative URL for API (nginx will proxy to backend)
echo "=== Generating config.js ==="
cat > /usr/share/nginx/html/config.js <<EOF
window.ENV = {
    API_URL: ''
};
EOF

cat /usr/share/nginx/html/config.js

# Wait for backend to be ready
echo "=== Waiting for backend... ==="
for i in 1 2 3 4 5; do
    if wget -q --spider http://backend:8000/api/health 2>/dev/null; then
        echo "Backend is ready!"
        break
    fi
    echo "Attempt $i: Backend not ready yet, waiting..."
    sleep 2
done

echo "=== Starting Nginx ==="
nginx -g 'daemon off;'