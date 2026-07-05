#!/usr/bin/env bash
#
# One-shot provisioner: get the Flight Meetup bot running 24/7 on a Linux VPS.
# Tested on AWS EC2 free tier with Ubuntu 24.04 and Amazon Linux 2023.
#
# Usage (from anywhere inside the cloned repo):
#     bash deploy/setup.sh
#
# It is safe to run again - it just reinstalls deps and refreshes the service.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="$(whoami)"
VENV="$REPO_DIR/venv"
SERVICE_NAME="flight-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "==> Repo:    $REPO_DIR"
echo "==> User:    $RUN_USER"
echo "==> Venv:    $VENV"
echo

# ── 1. system packages ─────────────────────────────────────────────────────
echo "==> Installing system packages (python3, venv, git)..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip git
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip git
else
    echo "!! Unsupported system: need apt-get (Ubuntu/Debian) or dnf (Amazon Linux/Fedora)."
    exit 1
fi

# ── 2. python venv + dependencies ──────────────────────────────────────────
echo "==> Creating virtualenv and installing dependencies..."
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$REPO_DIR/requirements.txt"

# ── 3. .env config ─────────────────────────────────────────────────────────
if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    echo
    echo "!! A fresh .env was created from the template."
    echo "!! Edit it and set TELEGRAM_BOT_TOKEN before starting the bot:"
    echo "!!     nano $REPO_DIR/.env"
fi

# ── 4. systemd service ─────────────────────────────────────────────────────
echo "==> Installing systemd service ($SERVICE_FILE)..."
sudo sed -e "s|__USER__|$RUN_USER|g" \
         -e "s|__WORKDIR__|$REPO_DIR|g" \
         -e "s|__VENV__|$VENV|g" \
         "$REPO_DIR/deploy/flight-bot.service" | sudo tee "$SERVICE_FILE" >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo
echo "============================================================"
echo " Setup complete."
echo
echo " 1. Add your token:     nano $REPO_DIR/.env"
echo " 2. Start the bot:      sudo systemctl start $SERVICE_NAME"
echo " 3. Watch the logs:     journalctl -u $SERVICE_NAME -f"
echo
echo " The bot now starts automatically on every reboot and"
echo " restarts itself if it ever crashes."
echo "============================================================"
