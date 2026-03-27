# CLAUDE.md — @peptidealpharesearch Agent System

This file tells Claude Code everything it needs to know about this project so every session starts with full context.

---

## What This Project Is

A 10-agent AI content system for the Instagram account **@peptidealpharesearch** (peptides / longevity / biohacking niche). The agents handle research, ideation, content creation, repurposing, and community management. Everything is controlled via Telegram. Claude Code is used for Canva carousel creation via MCP.

The owner is **not a developer** — all instructions must be non-technical. Never ask her to run terminal commands unless absolutely necessary.

---

## How to Start Everything

Double-click **`Start Peptides.command`** in the repo root. This starts:
- The Telegram bot (`bot.py`)
- The Flask dashboard at `http://localhost:5555`
- Opens the browser automatically

To check the bot is running in Claude Code terminal:
```
! ps aux | grep bot.py | grep -v grep
```

---

## Python Environment

- Python: `/usr/bin/python3` (macOS system Python 3.9)
- Always use `from typing import Optional, List` — never `X | Y` or `list[X]` syntax
- `load_dotenv(override=True)` on every agent/script to prevent inherited env vars
- All dependencies in `requirements.txt`

---

## Environment Variables (`.env`)

```
TELEGRAM_BOT_TOKEN=<your token — see .env>
TELEGRAM_ALLOWED_USER_ID=<your user ID — see .env>
LLM_PROVIDER=groq
GROQ_API_KEY=<your Groq key — see .env>
GEMINI_API_KEY=<your Gemini key — see .env>
IMGBB_API_KEY=<your ImgBB key — see .env>
```

All real values are in `.env` which is not committed to git.

`.env` is not committed to git.

---

## LLM Setup

All agents call `from tools.llm import call_llm`. Provider is set in `.env`:

| Provider | Setting | Model |
|---|---|---|
| Groq (default, free) | `LLM_PROVIDER=groq` | `llama-3.3-70b-versatile` |
| Anthropic | `LLM_PROVIDER=anthropic` | `claude-sonnet-4-6` |
| Ollama (local) | `LLM_PROVIDER=ollama` | `llama3.2` |

`call_llm(system=..., user=..., max_tokens=...)` — always use keyword arguments.

Groq uses HTTPAdapter with Retry to handle macOS DNS flakiness in background threads.

---

## Canva MCP

Canva is accessed via MCP tools in Claude Code (not from agents directly).

- **Primary template:** `DAHEVyvHuDg` (8-slide carousel)
- **Slide structure:** hook → supporting hook → problem → mechanism → insight → possibility → payoff → CTA
- **Skill file:** `canva-peptide-carousel.skill` — always use this when making a post

### Canva Rules
- Start a transaction → apply ALL edits → commit immediately in one uninterrupted sequence
- Never delay between edits and commit — transactions expire
- Slide 1 header: ALL CAPS, 10–15 words, no body text
- Slide 8 header: always "Follow @peptidealpharesearch"
- Use `perform-editing-operations` with `update_text` for copy, `update_fill` for images

### Canva Brand
```
Primary:      #0A1628  (deep navy)
Accent teal:  #00D4FF  (electric teal)
Accent gold:  #FFB347  (warm gold)
Text light:   #FFFFFF
Text dark:    #1A1A2E
```

---

## The 10 Agents

### Intelligence Tier
| Agent | File | Output |
|---|---|---|
| Research | `agents/research_agent.py` | `data/research_briefs/YYYY-MM-DD.md` |
| Trend Spotter | `agents/trend_spotter_agent.py` | `data/trend_alerts.md` |
| Analytics | `agents/analytics_agent.py` | `data/analytics/report_YYYY-MM-DD.md` |

### Strategy Tier
| Agent | File | Output |
|---|---|---|
| Ideation | `agents/ideation_agent.py` | `data/content_calendar.json` |

### Content Tier
| Agent | File | Output |
|---|---|---|
| Hook Tester | `agents/hook_tester_agent.py` | Saved into calendar entry under `hook_variants` |
| Caption | `agents/caption_agent.py` | `data/captions/YYYY-MM-DD-rank-N.md` |
| Content / Canva | via Claude Code + MCP | Canva design `DAHEVyvHuDg` |
| Repurpose | `agents/repurpose_agent.py` | `data/repurposed/YYYY-MM-DD-rank-N/` |

### Community Tier
| Agent | File | Output |
|---|---|---|
| Engagement | `agents/engagement_agent.py` | `data/engagement_queue.md` |
| Community Manager | `agents/community_manager_agent.py` | `data/reply_queue.md` |

---

## Telegram Bot Commands

All commands are in `bot.py`. Agent functions run in `loop.run_in_executor(None, ...)` to avoid blocking.

| Command | Function | What it does |
|---|---|---|
| `/research` | `cmd_research` | Runs research agent |
| `/ideation` | `cmd_ideation` | Runs ideation agent |
| `/list` | `cmd_list` | Shows calendar with inline Approve buttons |
| `/full` | `cmd_full` | Research + ideation pipeline |
| `/hooks [rank]` | `cmd_hooks` | 5 hook variants for an idea |
| `/caption [rank]` | `cmd_caption` | Full caption + hashtags |
| `/repurpose [rank]` | `cmd_repurpose` | Twitter + LinkedIn + Reel |
| `/trends` | `cmd_trends` | Reddit trend scan |
| `/engagement` | `cmd_engagement` | Outbound comment drafts |
| `/replies` | `cmd_replies` | Inbound comment reply drafts |
| `/analytics` | `cmd_analytics` | Performance report |
| `/status` | `cmd_status` | Health check |

- Bot uses `python-telegram-bot v20.7` in polling mode
- Authorised user ID: `1611046073`
- Approve button → marks idea `approved` in `content_calendar.json` → prompts user to open Claude Code

---

## Dashboard

- Flask app: `dashboard/app.py`, port `5555`
- Template: `dashboard/templates/index.html`
- `Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))` — explicit path required
- Bot starts dashboard as a subprocess: `subprocess.Popen([sys.executable, "dashboard/app.py"])`
- Polls `/api/status` every 3 seconds
- Shows: org chart (4 tiers, 10 nodes), activity timeline, content calendar, stats bar
- Agent live status derived from `data/activity_log.jsonl`

---

## Activity Logging

Every agent must log its activity so the dashboard shows live status:

```python
from tools.activity_log import log

log("agent_id", "running", "what it's doing")
log("agent_id", "done",    "what it completed")
log("agent_id", "error",   "what went wrong")
```

Agent IDs used in logs: `research`, `ideation`, `content`, `engagement`, `hook_tester`, `caption`, `repurpose`, `trend_spotter`, `community_manager`, `analytics`

Log file: `data/activity_log.jsonl` (one JSON object per line)

---

## Key Data Files

| File | Purpose |
|---|---|
| `data/content_calendar.json` | All ideas with status, hooks, captions, schedule |
| `data/research_briefs/` | Daily PubMed research output |
| `data/content_packages/` | Approved content ready for Canva |
| `data/captions/` | Generated Instagram captions |
| `data/repurposed/` | Twitter thread + LinkedIn + Reel scripts |
| `data/analytics/posts.json` | Manual post metrics (reach, likes, saves, etc.) |
| `data/trend_alerts.md` | Reddit trend scan output |
| `data/engagement_queue.md` | Outbound comment drafts |
| `data/reply_queue.md` | Inbound comment reply drafts |
| `data/inbound_comments.json` | Comments to reply to (manually updated) |

---

## Content Calendar Schema

Ideas in `data/content_calendar.json` follow this structure:

```json
{
  "rank": 1,
  "title": "Idea title",
  "hook": "Slide 1 hook text",
  "key_stat": "The core stat or claim",
  "slide_outline": ["slide topic 1", "slide topic 2"],
  "cta": "Suggested CTA",
  "hashtags": ["#peptides", "..."],
  "priority_score": 8.5,
  "recommended_post_day": "Wednesday",
  "recommended_post_time_est": "18:00",
  "status": "pending | approved | content_ready | posted",
  "created_at": "ISO timestamp",
  "hook_variants": [...],
  "caption_file": "data/captions/...",
  "repurposed_dir": "data/repurposed/..."
}
```

---

## Git Workflow

- Commit after every completed task
- Always push immediately after committing
- Branch + PR for large features; commit directly to `main` for fixes and small additions
- Commit message format: one clear summary line, then blank line, then bullet detail if needed
- Always end commits with: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

---

## Image Generation

- Gemini Imagen API requires a paid plan — free tier returns 429
- Pollinations.ai now requires authentication — cannot be used as free fallback
- Current approach: user generates images manually in Gemini web app, uploads to Canva, Claude places them using `update_fill` in Canva MCP
- `tools/image_generator.py` exists but is non-functional on free tier

---

## Known Issues / Watch Out For

- **Canva transaction expiry:** must start → edit → commit in one uninterrupted sequence. Never delay.
- **macOS DNS flakiness:** Groq API calls in background threads can fail with DNS errors. Fixed via HTTPAdapter retry in `tools/llm.py`.
- **Dashboard port conflict:** `Start Peptides.command` kills any existing process on port 5555 before starting. If dashboard shows old version, kill port 5555 manually and restart.
- **Browser caching:** dashboard serves `Cache-Control: no-store` headers. If old version persists, do Cmd+Shift+R hard refresh.
- **Telegram v20.7:** all handlers are async. Agent functions run in executor threads, never directly in async context.

---

## Making a New Post (Full Workflow in Claude Code)

When the user says "Make a post about [title]":

1. Read `data/content_calendar.json` to find the approved idea
2. Read the latest research brief in `data/research_briefs/`
3. Write 8 slides of copy following the structure in `tools/canva_helpers.py`
4. Use the `canva-peptide-carousel.skill` to populate design `DAHEVyvHuDg`
5. Start transaction → apply all 8 slides → commit immediately
6. Update idea status to `content_ready` in the calendar
7. Log completion with `tools/activity_log.log()`
8. Commit and push to git
