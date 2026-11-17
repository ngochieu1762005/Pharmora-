#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
echo "PharmaVision AI — http://127.0.0.1:8000"
exec python3 server.py
