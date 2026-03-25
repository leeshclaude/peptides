"""Append structured entries to data/activity_log.jsonl"""
import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "data" / "activity_log.jsonl"

def log(agent: str, status: str, message: str = ""):
    LOG_FILE.parent.mkdir(exist_ok=True)
    entry = {"ts": datetime.now().isoformat(), "agent": agent, "status": status, "message": message}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
