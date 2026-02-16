#!/bin/bash
# Mootoshi VPS Deployment Script
# Run as root on Ubuntu 24.04

set -e

echo "=========================================="
echo "  Mootoshi — VPS Deployment"
echo "=========================================="

# 1. System dependencies
echo ""
echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip ffmpeg git

# 2. Create service user
echo "[2/6] Creating mootoshi user..."
if ! id -u mootoshi &>/dev/null; then
    useradd -r -m -d /opt/mootoshi -s /bin/bash mootoshi
    echo "  User 'mootoshi' created."
else
    echo "  User 'mootoshi' already exists."
fi

# 3. Clone repo
echo "[3/6] Cloning repository..."
if [ -d /opt/mootoshi/src ]; then
    echo "  Repo already exists. Pulling latest..."
    cd /opt/mootoshi
    sudo -u mootoshi git pull
else
    cd /opt/mootoshi
    sudo -u mootoshi git clone https://github.com/dhroovmehta/bl0btoshii.git .
fi

# 4. Python virtual environment + dependencies
echo "[4/6] Setting up Python environment..."
sudo -u mootoshi python3 -m venv /opt/mootoshi/venv
sudo -u mootoshi /opt/mootoshi/venv/bin/pip install -q -r /opt/mootoshi/requirements.txt

# 5. Install systemd service
echo "[5/6] Installing systemd service..."
cp /opt/mootoshi/deploy/mootoshi.service /etc/systemd/system/mootoshi.service
systemctl daemon-reload
systemctl enable mootoshi

# 6. Check for .env
echo "[6/6] Checking configuration..."
if [ ! -f /opt/mootoshi/.env ]; then
    echo ""
    echo "  WARNING: /opt/mootoshi/.env not found!"
    echo "  Copy your .env file to /opt/mootoshi/.env before starting."
    echo "  Then run: systemctl start mootoshi"
else
    echo "  .env found. Starting service..."
    systemctl restart mootoshi
    sleep 2
    systemctl status mootoshi --no-pager
fi

echo ""
echo "=========================================="
echo "  Deployment complete!"
echo ""
echo "  Commands:"
echo "    systemctl start mootoshi    # Start bot"
echo "    systemctl stop mootoshi     # Stop bot"
echo "    systemctl status mootoshi   # Check status"
echo "    journalctl -u mootoshi -f   # View live logs"
echo "=========================================="
