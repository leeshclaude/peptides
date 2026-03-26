#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# @peptidealpharesearch — Start Everything
# Double-click this file in Finder to launch the bot + dashboard.
# ─────────────────────────────────────────────────────────────────────────────

# Go to the repo folder (same folder as this file)
cd "$(dirname "$0")"

echo ""
echo "  🧬  @peptidealpharesearch"
echo "  ─────────────────────────────────"
echo "  Starting Telegram bot + dashboard..."
echo ""

# Check Python is available
if ! command -v python3 &> /dev/null; then
  echo "  ❌  Python 3 not found."
  echo "  Install it from https://www.python.org/downloads/"
  read -p "  Press Enter to close..."
  exit 1
fi

# Kill anything already running on port 5555 (old dashboard processes)
OLD_PID=$(lsof -ti:5555 2>/dev/null)
if [ -n "$OLD_PID" ]; then
  echo "  🔄  Stopping old dashboard (pid $OLD_PID)..."
  kill -9 $OLD_PID 2>/dev/null
  sleep 1
fi

# Kill any leftover bot or dashboard python processes from this repo
pkill -f "bot.py" 2>/dev/null
pkill -f "dashboard/app.py" 2>/dev/null
sleep 1

# Install dependencies quietly if missing
python3 -c "import telegram" 2>/dev/null || {
  echo "  Installing dependencies..."
  python3 -m pip install -r requirements.txt -q
}

echo "  ✅  All clear — starting fresh..."
echo "  ✅  Dashboard will open at http://localhost:5555"
echo ""
echo "  Leave this window open while you're working."
echo "  Close it to stop everything."
echo ""

# Open the dashboard in the browser after a short delay (background)
(sleep 4 && open http://localhost:5555) &

# Start the bot (this also auto-starts the dashboard inside)
python3 bot.py
