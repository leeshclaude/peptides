# @peptidealpharesearch — Multi-Agent Content System

Automated content pipeline for the @peptidealpharesearch Instagram account (peptides / longevity / biohacking niche). A team of 10 AI agents handles research, content creation, repurposing, and community management — all controlled from Telegram.

---

## How to Start

**Double-click `Start Peptides.command`** in this folder.

That's it. It will:
- Start the Telegram bot
- Start the dashboard at [http://localhost:5555](http://localhost:5555)
- Open the dashboard in your browser automatically

To stop everything, close the Terminal window.

---

## Dashboard

Open [http://localhost:5555](http://localhost:5555) to see:

- **Org chart** — all 10 agents across 4 tiers, with live status (idle / running / done / error)
- **Activity timeline** — real-time log of every agent task
- **Content calendar** — all ideas with status and scheduled day
- **Stats bar** — brief age, pending ideas, approved, posted

---

## Telegram Commands

### Core Pipeline
| Command | What it does |
|---|---|
| `/research` | Fetches PubMed studies → saves research brief |
| `/ideation` | Reads latest brief → generates 7 ranked ideas |
| `/list` | Shows calendar with Approve buttons |
| `/full` | Runs research + ideation back to back |

### Content
| Command | What it does |
|---|---|
| `/hooks [rank]` | Generates 5 hook variants for an idea |
| `/caption [rank]` | Writes full caption + 30 hashtags + disclaimer |
| `/repurpose [rank]` | Converts carousel → Twitter thread + LinkedIn + Reel script |

### Intelligence
| Command | What it does |
|---|---|
| `/trends` | Scans Reddit for trending peptide topics |
| `/engagement` | Drafts comments for competitor posts |
| `/replies` | Drafts replies to your inbound comments |
| `/analytics` | Generates performance report from your post data |

### Utility
| Command | What it does |
|---|---|
| `/status` | Pipeline health check |
| `/help` | Shows command list |

---

## The 10 Agents

### Intelligence Tier
| Agent | What it does | Output |
|---|---|---|
| **Research** | Fetches PubMed studies + competitor intel | `data/research_briefs/YYYY-MM-DD.md` |
| **Trend Spotter** | Scans Reddit for niche topic spikes | `data/trend_alerts.md` |
| **Analytics** | Tracks post performance + feeds signals back to ideation | `data/analytics/report_YYYY-MM-DD.md` |

### Strategy Tier
| Agent | What it does | Output |
|---|---|---|
| **Ideation** | Synthesises research → 7 ranked carousel ideas | `data/content_calendar.json` |

### Content Tier
| Agent | What it does | Output |
|---|---|---|
| **Hook Tester** | Generates 5 hook variants (curiosity / shock / authority / relatability / FOMO) | Saved to calendar entry |
| **Caption** | Writes full Instagram caption + 30 hashtags + disclaimer | `data/captions/` |
| **Content / Canva** | Populates Canva carousel template with slide copy | Canva design (via Claude Code) |
| **Repurpose** | Converts carousel → Twitter thread + LinkedIn post + Reel script | `data/repurposed/` |

### Community Tier
| Agent | What it does | Output |
|---|---|---|
| **Engagement** | Drafts outbound comments on competitor posts | `data/engagement_queue.md` |
| **Community Manager** | Drafts 3 reply options per inbound comment | `data/reply_queue.md` |

---

## Daily Workflow

```
Morning
  /full           → fresh research + new ideas
  /list           → approve your favourite idea
  /hooks          → pick the best hook
  /caption        → generate the caption

Content creation
  Open Claude Code → "Make a post about [title]"
  Claude uses Canva MCP to build the carousel

Before posting
  /trends         → check what's spiking
  /repurpose      → prepare Twitter + LinkedIn versions

After posting
  Add metrics to data/analytics/posts.json
  /replies        → draft replies to comments
  /analytics      → weekly performance review
```

---

## File Structure

```
peptides/
├── Start Peptides.command   ← double-click to start everything
├── bot.py                   ← Telegram bot (10 commands)
├── agents/
│   ├── research_agent.py
│   ├── ideation_agent.py
│   ├── content_agent.py
│   ├── engagement_agent.py
│   ├── hook_tester_agent.py
│   ├── caption_agent.py
│   ├── repurpose_agent.py
│   ├── trend_spotter_agent.py
│   ├── community_manager_agent.py
│   └── analytics_agent.py
├── tools/
│   ├── llm.py               ← LLM abstraction (Groq / Anthropic / Ollama)
│   ├── pubmed.py            ← PubMed search wrapper
│   ├── activity_log.py      ← logs to data/activity_log.jsonl
│   ├── image_generator.py   ← Imagen → ImgBB pipeline
│   └── canva_helpers.py     ← Canva template config
├── dashboard/
│   ├── app.py               ← Flask server (port 5555)
│   └── templates/index.html ← org chart dashboard UI
├── data/
│   ├── research_briefs/     ← daily research output
│   ├── content_calendar.json
│   ├── content_packages/    ← approved content ready for Canva
│   ├── captions/            ← generated captions
│   ├── repurposed/          ← Twitter + LinkedIn + Reel scripts
│   ├── analytics/           ← performance reports + posts.json
│   ├── trend_alerts.md
│   ├── engagement_queue.md
│   ├── reply_queue.md
│   └── inbound_comments.json
├── prompts/                 ← system prompts per agent
├── .env                     ← API keys (not committed)
└── requirements.txt
```

---

## Tracking Post Performance

After each post, add the metrics to `data/analytics/posts.json`:

```json
{
  "date": "2026-03-27",
  "title": "Your post title",
  "format": "carousel",
  "reach": 1200,
  "likes": 145,
  "saves": 89,
  "shares": 12,
  "comments": 23,
  "follows_from_post": 8,
  "post_time": "18:00",
  "post_day": "Friday",
  "hook": "Your slide 1 hook text"
}
```

Then run `/analytics` in Telegram to get a full performance report.

---

## Replying to Comments

Add inbound comments to `data/inbound_comments.json`:

```json
[
  {
    "username": "@their_handle",
    "comment": "What they said on your post",
    "post": "Your post title"
  }
]
```

Then run `/replies` in Telegram to get 3 reply options per comment.

---

## Tech Stack

- **Python 3.9+**
- **LLM:** Groq free tier (llama-3.3-70b-versatile) — swap to Anthropic via `.env`
- **Telegram:** python-telegram-bot v20.7
- **Canva:** via MCP in Claude Code
- **Dashboard:** Flask + Tailwind CSS
- **Image generation:** Gemini Imagen API → ImgBB hosting
