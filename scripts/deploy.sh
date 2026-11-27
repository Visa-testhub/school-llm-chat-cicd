#!/usr/bin/env bash

set -euo pipefail

REVISION="${1:-}"
APP_DIR=/opt/chatapp/app
VENV=/opt/chatapp/venv
ENV_FILE=/etc/chatapp/chatapp.env
SOCKET=/run/chatapp/gunicorn.sock
SNIPPET=/etc/nginx/snippets/chatapp.conf
DB_NAME=chatapp


# Validate the supplied Git commit SHA
if [[ ! "$REVISION" =~ ^[0-9a-f]{40}$ ]]; then
    echo "ERROR: A valid Git commit SHA is required." >&2
    exit 1
fi

cd "$APP_DIR"

echo "==> Deploying revision $REVISION"


# Verify production configuration exists
sudo -n test -s "$ENV_FILE"

if ! sudo -n grep -REq \
    '^[[:space:]]*include[[:space:]]+(/etc/nginx/)?snippets/chatapp\.conf[[:space:]]*;' \
    /etc/nginx/sites-enabled/; then

    echo "ERROR: Nginx chatapp include is missing." >&2
    exit 1
fi


# Install Python dependencies
echo "==> Installing Python dependencies"

if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install -r requirements.txt


# Apply database schema
echo "==> Updating MySQL schema"

sudo -n mysql "$DB_NAME" < deploy/sql/schema.sql


# Update Nginx configuration
echo "==> Updating Nginx configuration"

sudo -n cp -p "$SNIPPET" "$SNIPPET.bak"

sudo -n install -m 644 \
    deploy/nginx/chatapp.conf "$SNIPPET"

if ! sudo -n nginx -t; then
    echo "ERROR: Invalid Nginx configuration." >&2
    echo "Restoring previous configuration." >&2

    sudo -n mv "$SNIPPET.bak" "$SNIPPET"
    exit 1
fi

if ! sudo -n systemctl reload nginx; then
    echo "ERROR: Nginx reload failed." >&2

    sudo -n mv "$SNIPPET.bak" "$SNIPPET"
    sudo -n nginx -t && sudo -n systemctl reload nginx || true

    exit 1
fi

sudo -n rm -f "$SNIPPET.bak"


# Update systemd configuration
echo "==> Updating systemd service"

sudo -n install -m 644 \
    deploy/systemd/chatapp.service \
    /etc/systemd/system/chatapp.service

sudo -n systemctl daemon-reload
sudo -n systemctl enable chatapp


# Record deployed revision
echo "==> Writing revision file"

printf '%s\n' "$REVISION" > REVISION


# Restart only our application
echo "==> Restarting chatapp"

sudo -n systemctl restart chatapp


# Verify the running application version
echo "==> Checking application health"

for attempt in $(seq 1 20); do

    if actual=$(sudo -n -u www-data curl -fsS \
        --max-time 3 \
        --unix-socket "$SOCKET" \
        http://localhost/health 2>/dev/null) \
        && [[ "$actual" == "$REVISION" ]]; then

        echo "SUCCESS: Revision $REVISION is running."
        exit 0
    fi

    echo "Waiting for application ($attempt/20)"
    sleep 2

done

echo "ERROR: Application did not report the expected revision." >&2

sudo -n journalctl -u chatapp -n 50 --no-pager >&2

exit 1
