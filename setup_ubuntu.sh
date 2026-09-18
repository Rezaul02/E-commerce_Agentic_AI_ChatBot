#!/usr/bin/env bash
# ============================================================
# Ubuntu setup — Docker chhara
# Cholao:  bash setup_ubuntu.sh
# Tested: Ubuntu 22.04 / 24.04
# ============================================================
set -e

echo "==> 1/5  System package update"
sudo apt update

echo "==> 2/5  Python + build tools install"
sudo apt install -y python3 python3-venv python3-pip build-essential curl

echo "==> 3/5  Redis install (Docker er poriborte native service)"
sudo apt install -y redis-server

# systemd diye manage korar jonno
sudo sed -i 's/^supervised .*/supervised systemd/' /etc/redis/redis.conf || true
# shudhu localhost e bind thakuk (nirapotta)
sudo sed -i 's/^# *bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf || true
# RAM vorti hole purono key age muche felbe (chat history er jonno upojukto)
if ! grep -q "^maxmemory-policy" /etc/redis/redis.conf; then
  echo "maxmemory-policy allkeys-lru" | sudo tee -a /etc/redis/redis.conf > /dev/null
fi

sudo systemctl enable redis-server
sudo systemctl restart redis-server
sleep 1
echo -n "    Redis check: "
redis-cli ping

echo "==> 4/5  Virtualenv toiri + dependency install"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> 5/5  .env toiri"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    ⚠️  .env banano holo — ekhon OPENAI_API_KEY bosan:  nano .env"
else
  echo "    .env age thekei ache, skip kora holo"
fi

echo ""
echo "✅ Setup shesh. Ekhon cholao:  bash run_all.sh"
