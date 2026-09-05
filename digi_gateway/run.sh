#!/usr/bin/with-contenv bashio
set -euo pipefail

export DIGI_SMART_DATA_DIR=/data
export DIGI_SMART_ENTITIES=/data/entities.json
export DIGI_SMART_VERIFY_TLS=true

if [ ! -f /data/entities.json ]; then
  printf '%s\n' '{"auto_discover":true,"entities":[]}' > /data/entities.json
  chmod 600 /data/entities.json
fi

exec python3 /app/digi_gateway.py
