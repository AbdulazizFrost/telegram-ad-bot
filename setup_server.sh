#!/bin/bash
set -e

echo "=== Telegram Anti-Ad Moderation Bot: Avtomatik o'rnatish ==="

# 1. Update system & install prerequisites
apt-get update
apt-get install -y python3 python3-pip python3-venv git curl

# 2. Setup project directory
BOT_DIR="/opt/tg_ad_bot"
if [ ! -d "$BOT_DIR" ]; then
    mkdir -p "$BOT_DIR"
fi

echo "Loyihani $BOT_DIR katalogiga nusxalash/sozlash..."
cp -r . "$BOT_DIR/" || true
cd "$BOT_DIR"

# 3. Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 4. Install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Ensure data and logs directories
mkdir -p data logs

# 6. Configure systemd service
cp bot.service /etc/systemd/system/tg_ad_bot.service
systemctl daemon-reload
systemctl enable tg_ad_bot
systemctl restart tg_ad_bot

echo "=== O'rnatish muvaffaqiyatli yakunlandi! ==="
echo "Holatni tekshirish: systemctl status tg_ad_bot"
echo "Loglarni ko'rish: journalctl -u tg_ad_bot -f"
