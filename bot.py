#!/usr/bin/env python3
"""
Telegram bot interface for @peptidealpharesearch agent system.

Commands:
  /start        — Welcome + command list
  /status       — Pipeline health check
  /research     — Run research agent → new brief
  /ideation     — Run ideation agent → ranked ideas
  /list         — Show content calendar with approve buttons
  /engagement   — Run engagement agent → comment drafts
  /full         — Run research + ideation pipeline
  /hooks        — Generate 5 hook variants for latest approved idea
  /caption      — Write full caption + hashtags for latest approved idea
  /repurpose    — Convert latest idea into Twitter thread + LinkedIn + Reel script
  /trends       — Scan Reddit for trending peptide topics
  /replies      — Draft replies for inbound comments
  /analytics    — Generate performance analysis report
  /help         — Show commands

Run: python bot.py
"""

import asyncio
import json
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from pathlib import Path as _Path
from dotenv import load_dotenv

# Always load from the repo's own .env, overriding any inherited env vars
load_dotenv(dotenv_path=_Path(__file__).parent / ".env", override=True)
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ─── Config ───────────────────────────────────────────────────────────────────

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER_ID = int(os.environ["TELEGRAM_ALLOWED_USER_ID"])

REPO_ROOT = Path(__file__).parent
BRIEFS_DIR = REPO_ROOT / "data" / "research_briefs"
CALENDAR_FILE = REPO_ROOT / "data" / "content_calendar.json"
ENGAGEMENT_FILE = REPO_ROOT / "data" / "engagement_queue.md"
PACKAGES_DIR = REPO_ROOT / "data" / "content_packages"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Auth Guard ───────────────────────────────────────────────────────────────

def is_allowed(update: Update) -> bool:
    return update.effective_user.id == ALLOWED_USER_ID


async def deny(update: Update) -> None:
    await update.message.reply_text("Not authorised.")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_calendar() -> dict:
    if CALENDAR_FILE.exists():
        return json.loads(CALENDAR_FILE.read_text())
    return {"ideas": []}


def get_pipeline_status() -> str:
    lines = ["@peptidealpharesearch Pipeline\n"]

    briefs = sorted(BRIEFS_DIR.glob("*.md"), reverse=True) if BRIEFS_DIR.exists() else []
    if briefs:
        age = (datetime.now() - datetime.fromtimestamp(briefs[0].stat().st_mtime)).days
        lines.append(f"📄 Brief: {briefs[0].name} ({age}d old)")
    else:
        lines.append("📄 Brief: None — run /research")

    if CALENDAR_FILE.exists():
        cal = load_calendar()
        ideas = cal.get("ideas", [])
        pending  = sum(1 for i in ideas if i.get("status") == "pending")
        approved = sum(1 for i in ideas if i.get("status") == "approved")
        ready    = sum(1 for i in ideas if i.get("status") == "content_ready")
        posted   = sum(1 for i in ideas if i.get("status") == "posted")
        lines.append(f"📅 Calendar: {pending} pending · {approved} approved · {ready} ready · {posted} posted")
        if pending:
            top = next(i for i in ideas if i.get("status") == "pending")
            lines.append(f"   Top idea: {top['title']}")
    else:
        lines.append("📅 Calendar: Empty — run /ideation")

    if ENGAGEMENT_FILE.exists():
        age_h = (datetime.now() - datetime.fromtimestamp(ENGAGEMENT_FILE.stat().st_mtime)).total_seconds() / 3600
        lines.append(f"💬 Engagement: Updated {age_h:.0f}h ago")
    else:
        lines.append("💬 Engagement: None — run /engagement")

    return "\n".join(lines)


def format_ideas_message(ideas: list) -> tuple[str, Optional[InlineKeyboardMarkup]]:
    """Format ideas list with inline approve buttons for pending ones."""
    if not ideas:
        return "No ideas in calendar yet. Run /ideation first.", None

    lines = ["Content Calendar\n"]
    buttons = []

    status_emoji = {
        "pending": "⏳",
        "approved": "✅",
        "content_ready": "🎨",
        "posted": "📸",
    }

    for idea in ideas[:10]:  # cap at 10
        status = idea.get("status", "?")
        emoji = status_emoji.get(status, "•")
        rank = idea.get("rank", "?")
        title = idea.get("title", "Untitled")
        score = idea.get("priority_score", 0)
        day = idea.get("recommended_post_day", "")
        lines.append(f"{emoji} #{rank} {title} [{score:.0f}] — {day}")

        if status == "pending":
            buttons.append([
                InlineKeyboardButton(
                    f"Approve #{rank}: {title[:30]}",
                    callback_data=f"approve:{rank}",
                )
            ])

    text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    return text, keyboard


# ─── Agent runners (blocking — run in thread pool) ────────────────────────────

def _run_research() -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.research_agent import run
    output = run()
    content = output.read_text()
    # Trim for Telegram (4096 char limit)
    if len(content) > 3800:
        content = content[:3800] + "\n\n_...truncated. Full brief saved locally._"
    return content


def _run_ideation() -> tuple[str, list]:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.ideation_agent import run
    run()
    cal = load_calendar()
    ideas = cal.get("ideas", [])
    new_ideas = [i for i in ideas if i.get("status") == "pending"][:7]
    return new_ideas


def _run_engagement() -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.engagement_agent import run
    run()
    if ENGAGEMENT_FILE.exists():
        content = ENGAGEMENT_FILE.read_text()
        if len(content) > 3800:
            content = content[:3800] + "\n\n_...truncated. Full queue saved locally._"
        return content
    return "Engagement queue generated."


def _run_hooks(rank: Optional[int] = None) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.hook_tester_agent import run
    variants = run(rank=rank)
    lines = ["Hook Variants Generated\n"]
    for v in variants:
        lines.append(f"[{v['angle'].upper()}]\n{v['hook']}\n_{v['reasoning']}_\n")
    return "\n".join(lines)


def _run_caption(rank: Optional[int] = None) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.caption_agent import run
    path = run(rank=rank)
    content = path.read_text()
    if len(content) > 3800:
        content = content[:3800] + "\n\n_...truncated. Full caption saved locally._"
    return content


def _run_repurpose(rank: Optional[int] = None) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.repurpose_agent import run
    out_dir = run(rank=rank)
    lines = [f"Repurposed Content Ready\n\nFiles saved to: {out_dir.name}\n"]
    for fname in ["twitter_thread.txt", "linkedin_post.txt", "reel_script.txt"]:
        fpath = out_dir / fname
        if fpath.exists():
            lines.append(f"\n--- {fname} ---\n{fpath.read_text()[:600]}...\n")
    return "\n".join(lines)[:4000]


def _run_trends() -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.trend_spotter_agent import run
    path = run()
    content = path.read_text()
    if len(content) > 3800:
        content = content[:3800] + "\n\n_...truncated. Full report saved locally._"
    return content


def _run_replies() -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.community_manager_agent import run
    path = run()
    content = path.read_text()
    if len(content) > 3800:
        content = content[:3800] + "\n\n_...truncated. Full queue saved locally._"
    return content


def _run_analytics() -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.analytics_agent import run
    path = run()
    content = path.read_text()
    if len(content) > 3800:
        content = content[:3800] + "\n\n_...truncated. Full report saved locally._"
    return content



# ─── Command Handlers ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    text = (
        "@peptidealpharesearch Bot\n\n"
        "Your agent control panel.\n\n"
        "── Core Pipeline ──\n"
        "/research — Run research agent\n"
        "/ideation — Generate content ideas\n"
        "/list — View calendar + approve ideas\n"
        "/full — Research + ideation pipeline\n\n"
        "── Content ──\n"
        "/hooks [rank] — Generate 5 hook variants\n"
        "/caption [rank] — Write caption + hashtags\n"
        "/repurpose [rank] — Twitter + LinkedIn + Reel\n\n"
        "── Intelligence ──\n"
        "/trends — Scan Reddit for niche trends\n"
        "/engagement — Draft outbound comments\n"
        "/replies — Draft replies to inbound comments\n"
        "/analytics — Performance analysis report\n\n"
        "── Utility ──\n"
        "/status — Pipeline health check\n"
        "/help — Show this message"
    )
    await update.message.reply_text(text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)
    await update.message.reply_text(get_pipeline_status())


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    cal = load_calendar()
    ideas = cal.get("ideas", [])
    text, keyboard = format_ideas_message(ideas)
    await update.message.reply_text(text, reply_markup=keyboard)


async def cmd_research(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text("🔬 Running research agent... (1-2 minutes)")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_research)
        if len(result) > 3500:
            await msg.edit_text("✅ Research brief ready:")
            await update.message.reply_text(result[:4000])
        else:
            await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Research failed: {e}")


async def cmd_ideation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text("💡 Running ideation agent... (1-2 minutes)")

    loop = asyncio.get_event_loop()
    try:
        new_ideas = await loop.run_in_executor(None, _run_ideation)
        text, keyboard = format_ideas_message(new_ideas)
        await msg.edit_text(f"✅ {len(new_ideas)} ideas generated!\n\n" + text, reply_markup=keyboard)
    except FileNotFoundError:
        await msg.edit_text("❌ No research brief found. Run /research first.")
    except Exception as e:
        await msg.edit_text(f"❌ Ideation failed: {e}")


async def cmd_engagement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text("💬 Drafting engagement comments... (1-2 minutes)")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_engagement)
        await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Engagement agent failed: {e}")


async def cmd_hooks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    args = context.args
    rank = int(args[0]) if args else None
    msg = await update.message.reply_text(f"🎣 Generating hook variants{f' for #{rank}' if rank else ''}...")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: _run_hooks(rank))
        await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Hook tester failed: {e}")


async def cmd_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    args = context.args
    rank = int(args[0]) if args else None
    msg = await update.message.reply_text(f"✍️ Writing caption{f' for #{rank}' if rank else ''}...")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: _run_caption(rank))
        await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Caption agent failed: {e}")


async def cmd_repurpose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    args = context.args
    rank = int(args[0]) if args else None
    msg = await update.message.reply_text(f"♻️ Repurposing content{f' for #{rank}' if rank else ''}... (1-2 min)")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, lambda: _run_repurpose(rank))
        await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Repurpose agent failed: {e}")


async def cmd_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text("📈 Scanning Reddit for trends... (1-2 min)")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_trends)
        await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Trend spotter failed: {e}")


async def cmd_replies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text("💬 Drafting comment replies...")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_replies)
        await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Community manager failed: {e}")


async def cmd_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text("📊 Generating analytics report...")

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_analytics)
        await msg.edit_text(result[:4000])
    except Exception as e:
        await msg.edit_text(f"❌ Analytics agent failed: {e}")


async def cmd_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text("🚀 Running full pipeline: research → ideation... (2-4 minutes)")

    loop = asyncio.get_event_loop()
    try:
        await msg.edit_text("🔬 Step 1/2: Running research agent...")
        await loop.run_in_executor(None, _run_research)

        await msg.edit_text("💡 Step 2/2: Running ideation agent...")
        new_ideas = await loop.run_in_executor(None, _run_ideation)

        text, keyboard = format_ideas_message(new_ideas)
        await msg.edit_text(f"✅ Pipeline complete! {len(new_ideas)} ideas ready.\n\n" + text, reply_markup=keyboard)
    except Exception as e:
        await msg.edit_text(f"❌ Pipeline failed: {e}")


# ─── Inline Button Handler (approve idea) ─────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ALLOWED_USER_ID:
        return

    data = query.data
    if data.startswith("approve:"):
        rank = int(data.split(":")[1])

        try:
            cal = load_calendar()
            idea = next((i for i in cal.get("ideas", []) if i.get("rank") == rank), None)
            if not idea:
                await query.edit_message_text(f"❌ Idea #{rank} not found in calendar.")
                return

            idea["status"] = "approved"
            CALENDAR_FILE.write_text(json.dumps(cal, indent=2))

            title = idea.get("title", "the topic")
            await query.edit_message_text(
                f"Idea #{rank} approved!\n\n"
                f"Open Claude Code and say:\n"
                f"Make a post about {title}"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Approve failed: {e}")


# ─── Dashboard server (runs in background thread) ─────────────────────────────

def _start_dashboard() -> None:
    """Start the Flask dashboard on port 5555 in a background thread."""
    try:
        import importlib.util, sys as _sys
        dashboard_path = REPO_ROOT / "dashboard" / "app.py"
        spec = importlib.util.spec_from_file_location("dashboard_app", dashboard_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Silence Flask startup noise
        import logging as _log
        _log.getLogger("werkzeug").setLevel(_log.ERROR)
        module.app.run(host="127.0.0.1", port=5555, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Dashboard] Could not start: {e}")


def start_dashboard_thread() -> None:
    t = threading.Thread(target=_start_dashboard, daemon=True, name="dashboard")
    t.start()
    print("Dashboard: http://localhost:5555")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Starting @peptidealpharesearch bot...")
    print(f"Authorised user: {ALLOWED_USER_ID}")
    print(f"LLM provider: {os.environ.get('LLM_PROVIDER', 'groq')} / {os.environ.get('LLM_MODEL', 'default')}")
    print(f"GROQ key loaded: {bool(os.environ.get('GROQ_API_KEY'))}")
    print(f"ANTHROPIC key loaded: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")

    start_dashboard_thread()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("help",       cmd_help))
    app.add_handler(CommandHandler("status",     cmd_status))
    app.add_handler(CommandHandler("research",   cmd_research))
    app.add_handler(CommandHandler("ideation",   cmd_ideation))
    app.add_handler(CommandHandler("list",       cmd_list))
    app.add_handler(CommandHandler("engagement", cmd_engagement))
    app.add_handler(CommandHandler("full",       cmd_full))
    app.add_handler(CommandHandler("hooks",      cmd_hooks))
    app.add_handler(CommandHandler("caption",    cmd_caption))
    app.add_handler(CommandHandler("repurpose",  cmd_repurpose))
    app.add_handler(CommandHandler("trends",     cmd_trends))
    app.add_handler(CommandHandler("replies",    cmd_replies))
    app.add_handler(CommandHandler("analytics",  cmd_analytics))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
