#!/bin/sh
# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
# Generates a random PYSPUR_API_KEY and stores it in .env, creating .env from .env.example if needed.
# The key is yours to choose: any long random string works. Run it from anywhere:
#   ./scripts/generate_api_key.sh
set -eu

cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.example .env

if grep -q '^PYSPUR_API_KEY=.' .env; then
    echo "PYSPUR_API_KEY is already set in .env; leaving it unchanged."
    exit 0
fi

if command -v python3 >/dev/null 2>&1; then
    key=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
else
    key=$(openssl rand -base64 32 | tr -d '=+/\n')
fi

tmp=$(mktemp)
awk -v k="$key" '
    /^PYSPUR_API_KEY=/ { print "PYSPUR_API_KEY=" k; done = 1; next }
    { print }
    END { if (!done) print "PYSPUR_API_KEY=" k }
' .env > "$tmp"
mv "$tmp" .env
chmod 600 .env

echo "Wrote PYSPUR_API_KEY to .env. The app asks for this key in the browser:"
echo "$key"
