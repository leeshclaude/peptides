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

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

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
    lines = ["*@peptidealpharesearch Pipeline*\n"]

    # Research brief
    briefs = sorted(BRIEFS_DIR.glob("*.md"), reverse=True) if BRIEFS_DIR.exists() else []
    if briefs:
        age = (datetime.now() - datetime.fromtimestamp(briefs[0].stat().st_mtime)).days
        lines.append(f"📄 *Brief:* {briefs[0].name} ({age}d old)")
    else:
        lines.append("📄 *Brief:* None — run /research")

    # Calendar
    if CALENDAR_FILE.exists():
        cal = load_calendar()
        ideas = cal.get("ideas", [])
        pending  = sum(1 for i in ideas if i.get("status") == "pending")
        approved = sum(1 for i in ideas if i.get("status") == "approved")
        ready    = sum(1 for i in ideas if i.get("status") == "content_ready")
        posted   = sum(1 for i in ideas if i.get("status") == "posted")
        lines.append(f"📅 *Calendar:* {pending} pending · {approved} approved · {ready} ready · {posted} posted")
        if pending:
            top = next(i for i in ideas if i.get("status") == "pending")
            lines.append(f"   Top idea: _{top['title']}_")
    else:
        lines.append("📅 *Calendar:* Empty — run /ideation")

    # Engagement queue
    if ENGAGEMENT_FILE.exists():
        age_h = (datetime.now() - datetime.fromtimestamp(ENGAGEMENT_FILE.stat().st_mtime)).total_seconds() / 3600
        lines.append(f"💬 *Engagement:* Updated {age_h:.0f}h ago")
    else:
        lines.append("💬 *Engagement:* None — run /engagement")

    return "\n".join(lines)


def format_ideas_message(ideas: list) -> tuple[str, Optional[InlineKeyboardMarkup]]:
    """Format ideas list with inline approve buttons for pending ones."""
    if not ideas:
        return "No ideas in calendar yet\\. Run /ideation first\\.", None

    lines = ["*Content Calendar*\n"]
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
        lines.append(f"{emoji} *#{rank}* {title} \\[{score:.0f}\\] — {day}")

        if status == "pending":
            buttons.append([
                InlineKeyboardButton(
                    f"✅ Approve #{rank}: {title[:30]}",
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


def _run_content(idea_rank: int) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    from agents.content_agent import run
    package_path = run(idea_rank=idea_rank)
    package = json.loads(package_path.read_text())

    lines = [f"*Content ready: {package.get('design_title', '')}*\n"]
    for slide in package.get("slides", []):
        header = slide.get("header", "")
        body = slide.get("body", "")
        lines.append(f"*Slide {slide['slide_number']}* \\[{slide.get('role', '')}\\]")
        lines.append(f"_{header}_")
        if body:
            lines.append(body)
        lines.append("")

    lines.append(f"*Caption preview:*\n{package.get('caption', '')[:400]}\\.\\.\\.")
    return "\n".join(lines)


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


def _approve_and_create(idea_rank: int) -> str:
    return _run_content(idea_rank)


# ─── Command Handlers ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    text = (
        "*@peptidealpharesearch Bot*\n\n"
        "Your agent control panel\\.\n\n"
        "*/status* — Pipeline health check\n"
        "*/research* — Run research agent\n"
        "*/ideation* — Generate content ideas\n"
        "*/list* — View calendar \\+ approve ideas\n"
        "*/engagement* — Draft engagement comments\n"
        "*/full* — Research \\+ ideation pipeline\n"
        "*/help* — Show this message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)
    await update.message.reply_text(
        get_pipeline_status(), parse_mode=ParseMode.MARKDOWN_V2
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    cal = load_calendar()
    ideas = cal.get("ideas", [])
    text, keyboard = format_ideas_message(ideas)
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )


async def cmd_research(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text(
        "🔬 Running research agent\\.\\.\\. \\(this takes 1\\-2 minutes\\)",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_research)
        # Send as document if long, otherwise as message
        if len(result) > 3500:
            await msg.edit_text("✅ Research brief ready\\. Sending\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
            await update.message.reply_text(
                result[:4000], parse_mode=None
            )
        else:
            await msg.edit_text(result[:4000], parse_mode=None)
    except Exception as e:
        await msg.edit_text(f"❌ Research failed: {e}")


async def cmd_ideation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text(
        "💡 Running ideation agent\\.\\.\\. \\(1\\-2 minutes\\)",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    loop = asyncio.get_event_loop()
    try:
        new_ideas = await loop.run_in_executor(None, _run_ideation)
        text, keyboard = format_ideas_message(new_ideas)
        await msg.edit_text(
            f"✅ {len(new_ideas)} ideas generated\\!\n\n" + text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )
    except FileNotFoundError:
        await msg.edit_text("❌ No research brief found\\. Run /research first\\.", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        await msg.edit_text(f"❌ Ideation failed: {e}")


async def cmd_engagement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text(
        "💬 Drafting engagement comments\\.\\.\\. \\(1\\-2 minutes\\)",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _run_engagement)
        await msg.edit_text(result[:4000], parse_mode=None)
    except Exception as e:
        await msg.edit_text(f"❌ Engagement agent failed: {e}")


async def cmd_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return await deny(update)

    msg = await update.message.reply_text(
        "🚀 Running full pipeline: research → ideation\\.\\.\\. \\(2\\-4 minutes\\)",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    loop = asyncio.get_event_loop()
    try:
        await msg.edit_text("🔬 Step 1/2: Running research agent\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
        await loop.run_in_executor(None, _run_research)

        await msg.edit_text("💡 Step 2/2: Running ideation agent\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
        new_ideas = await loop.run_in_executor(None, _run_ideation)

        text, keyboard = format_ideas_message(new_ideas)
        await msg.edit_text(
            f"✅ Pipeline complete\\! {len(new_ideas)} ideas ready\\.\n\n" + text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=keyboard,
        )
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
        await query.edit_message_text(
            f"🎨 Generating content package for idea \\#{rank}\\.\\.\\. \\(1\\-2 minutes\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, _approve_and_create, rank)
            # Send in chunks if long
            chunks = [result[i:i+4000] for i in range(0, min(len(result), 8000), 4000)]
            await query.edit_message_text(
                f"✅ Content package ready for idea \\#{rank}\\!",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            for chunk in chunks:
                await query.message.reply_text(chunk[:4000], parse_mode=None)
            await query.message.reply_text(
                "Open Claude Code and say:\n\"Update Canva with the latest content package\""
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Content generation failed: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Starting @peptidealpharesearch bot...")
    print(f"Authorised user: {ALLOWED_USER_ID}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("help",       cmd_help))
    app.add_handler(CommandHandler("status",     cmd_status))
    app.add_handler(CommandHandler("research",   cmd_research))
    app.add_handler(CommandHandler("ideation",   cmd_ideation))
    app.add_handler(CommandHandler("list",       cmd_list))
    app.add_handler(CommandHandler("engagement", cmd_engagement))
    app.add_handler(CommandHandler("full",       cmd_full))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
