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

# Install dependencies quietly if missing
python3 -c "import telegram" 2>/dev/null || {
  echo "  Installing dependencies..."
  python3 -m pip install -r requirements.txt -q
}

echo "  ✅  Bot starting..."
echo "  ✅  Dashboard will open at http://localhost:5555"
echo ""
echo "  Leave this window open while you're working."
echo "  Close it to stop everything."
echo ""

# Open the dashboard in the browser after a short delay (background)
(sleep 3 && open http://localhost:5555) &

# Start the bot (this also auto-starts the dashboard inside)
python3 bot.py
