#!/usr/bin/env bash
# ============================================================
# Tinta service ek shathe cholanor script (Docker chhara)
#   :8001  Dummy API   (Flask)
#   :8000  Chat Server (Flask)
#   :8501  Streamlit UI
# Cholao:  bash run_all.sh     |  Bondho:  Ctrl+C
# ============================================================
set -e

cd "$(dirname "$0")"
source venv/bin/activate
export PYTHONPATH="$PWD"

mkdir -p logs

echo "==> Redis check"
redis-cli ping > /dev/null 2>&1 || { echo "❌ Redis cholche na. Cholao: sudo systemctl start redis-server"; exit 1; }
echo "    Redis OK"

cleanup() {
  echo ""
  echo "==> Shob service bondho kora hocche..."
  kill $API_PID $CHAT_PID $UI_PID 2>/dev/null || true
  wait 2>/dev/null || true
  echo "    Done."
}
trap cleanup EXIT INT TERM

echo "==> Dummy API (:8001)"
python -m dummy_api.main > logs/dummy_api.log 2>&1 &
API_PID=$!
sleep 3

echo "==> Chat Server (:8000)"
python -m app.server > logs/chat_server.log 2>&1 &
CHAT_PID=$!
sleep 3

echo "==> Streamlit UI (:8501)"
streamlit run ui/streamlit_app.py --server.port 8501 --server.headless true > logs/ui.log 2>&1 &
UI_PID=$!
sleep 2

echo ""
echo "✅ Shob cholche:"
echo "   Dummy API   : http://localhost:8001/"
echo "   Chat Server : http://localhost:8000/health"
echo "   UI          : http://localhost:8501"
echo ""
echo "   Log dekhte  : tail -f logs/chat_server.log"
echo "   Bondho korte: Ctrl+C"

wait
