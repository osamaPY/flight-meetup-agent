#!/usr/bin/env bash
#
# Pull the latest code, refresh dependencies and restart the bot.
# Run this on the VPS whenever you push new changes to GitHub.
#
#     bash deploy/update.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Pulling latest changes..."
git pull --ff-only

echo "==> Updating dependencies..."
"$REPO_DIR/venv/bin/pip" install -r requirements.txt

echo "==> Restarting the bot..."
sudo systemctl restart flight-bot

echo "==> Done. Tail the logs with:  journalctl -u flight-bot -f"
