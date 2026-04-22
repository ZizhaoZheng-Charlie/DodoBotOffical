#!/usr/bin/env bash
#
# EC2 user-data bootstrap for DodoBot on Amazon Linux 2023 (t3.micro free tier).
# Idempotent: safe to re-run.
#
# Expected to be passed as --user-data when running `aws ec2 run-instances`,
# or executed manually with:
#   sudo REPO_URL=https://github.com/OWNER/REPO.git bash bootstrap.sh
#
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/ZizhaoZheng-Charlie/DodoBotOffical.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/dodobot}"
SERVICE_USER="${SERVICE_USER:-dodobot}"

log() { echo "[bootstrap] $*"; }

# ---- packages ---------------------------------------------------------------
log "Installing system packages"
dnf -y update
dnf -y install git python3.12 python3.12-pip tar xz

# ffmpeg is not in the default AL2023 repos; use the static build.
if ! command -v ffmpeg >/dev/null 2>&1; then
    log "Installing ffmpeg static build"
    TMP=$(mktemp -d)
    curl -fsSL -o "$TMP/ff.tar.xz" \
        https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
    tar -C "$TMP" -xf "$TMP/ff.tar.xz"
    install -m 0755 "$TMP"/ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg
    install -m 0755 "$TMP"/ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe
    rm -rf "$TMP"
fi
ffmpeg -version | head -n 1

# ---- service account --------------------------------------------------------
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    log "Creating service user $SERVICE_USER"
    useradd --system --home "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# ---- code checkout ----------------------------------------------------------
if [ ! -d "$INSTALL_DIR/.git" ]; then
    log "Cloning $REPO_URL into $INSTALL_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
else
    log "Updating existing checkout"
    git -C "$INSTALL_DIR" fetch origin
    git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
fi

# ---- virtualenv + deps ------------------------------------------------------
if [ ! -x "$INSTALL_DIR/.venv/bin/python" ]; then
    log "Creating virtualenv"
    python3.12 -m venv "$INSTALL_DIR/.venv"
fi
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# ---- .env placeholder -------------------------------------------------------
if [ ! -f "$INSTALL_DIR/.env" ]; then
    log "Creating empty .env - upload your secrets after bootstrap"
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod 600 "$INSTALL_DIR/.env"

# ---- systemd ----------------------------------------------------------------
install -m 0644 "$INSTALL_DIR/deploy/dodobot.service" /etc/systemd/system/dodobot.service
systemctl daemon-reload
systemctl enable dodobot.service

# Only start if DISCORD_TOKEN is actually populated - otherwise we crash-loop.
if grep -q '^DISCORD_TOKEN=.\+' "$INSTALL_DIR/.env"; then
    log "Starting dodobot"
    systemctl restart dodobot
else
    log "DISCORD_TOKEN empty in .env - service enabled but NOT started."
    log "After uploading .env, run: sudo systemctl start dodobot"
fi

log "Bootstrap complete."
