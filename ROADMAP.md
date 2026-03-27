# @peptidealpharesearch — Agent System Roadmap

---

## Phase 1 — Foundation ✅ Complete

The core pipeline is built and running.

- [x] Research Agent — PubMed fetching + daily briefs
- [x] Ideation Agent — ranked content ideas from research
- [x] Content Agent — slide copy generation
- [x] Engagement Agent — outbound competitor comment drafts
- [x] Telegram bot — full command interface
- [x] Canva MCP integration — Claude populates carousel templates
- [x] Activity log — structured JSON event stream
- [x] `Start Peptides.command` — one double-click to start everything

---

## Phase 2 — Agent Team ✅ Complete

Six specialist agents added to the team.

- [x] Hook Tester Agent — 5 hook variants per idea (curiosity / shock / authority / relatability / FOMO)
- [x] Caption Agent — full caption + 30 hashtags + disclaimer
- [x] Repurpose Agent — carousel → Twitter thread + LinkedIn post + Reel script
- [x] Trend Spotter Agent — Reddit niche scanning
- [x] Community Manager Agent — inbound comment reply drafts
- [x] Analytics Agent — performance tracking + ideation feedback
- [x] Org chart dashboard — live 10-agent view at localhost:5555
- [x] CLAUDE.md — full system context for every Claude Code session
- [x] README.md — user-facing documentation

---

## Phase 3 — Image Automation 🔜 Next

Remove the last manual step in carousel creation.

- [ ] Find a reliable free image generation API (stable diffusion, FLUX, or similar)
- [ ] Auto-generate 8 slide background images from a per-slide prompt
- [ ] Upload images to Canva and place them via `update_fill`
- [ ] Add `/images` Telegram command to trigger image generation for an approved idea
- [ ] Full end-to-end: approve idea → Claude generates copy + images → populates Canva

**Why this matters:** Currently images are generated manually in Gemini web app. Automating this removes the only step that requires leaving Telegram or Claude Code.

---

## Phase 4 — Scheduling & Auto-Post 🔜 Next

Post at the right time without manual effort.

- [ ] Build Scheduler Agent — queues approved, content-ready posts for optimal times
- [ ] Integrate with Instagram Graph API (requires Meta Business account)
- [ ] `/schedule [rank] [day] [time]` Telegram command
- [ ] Auto-post carousels + captions at scheduled times
- [ ] Notify via Telegram when a post goes live
- [ ] Update `content_calendar.json` status to `posted` automatically

**Why this matters:** Currently posting is fully manual — copy the caption, upload to Instagram. This closes the loop.

---

## Phase 5 — Analytics Feedback Loop 🔜 Next

Let performance data drive what gets made next.

- [ ] Connect Analytics Agent output to Ideation Agent input
- [ ] Track which hook angles (curiosity / shock / authority) perform best
- [ ] Track which topics get the most saves — promote similar topics in future ideation
- [ ] Track best posting times per content type
- [ ] Weekly Telegram performance digest — auto-sent every Monday morning
- [ ] `/analytics weekly` command for summary report

**Why this matters:** Right now analytics are tracked manually. This turns past performance into a signal that shapes the next week's content.

---

## Phase 6 — Multi-Platform Publishing 🔜 Future

Distribute every carousel automatically across platforms.

- [ ] Auto-post Twitter/X thread after Instagram goes live
- [ ] Auto-post LinkedIn version after Instagram goes live
- [ ] Schedule Reel script reminders via Telegram
- [ ] Track engagement across all platforms in the analytics dashboard
- [ ] Platform-specific performance comparison (which format works best where)

**Why this matters:** The Repurpose Agent already writes the content — this automates the publishing so one carousel becomes four posts with zero extra effort.

---

## Phase 7 — Growth Intelligence 🔜 Future

Move from reactive to predictive content strategy.

- [ ] Trend Spotter Agent runs on a daily schedule (auto, not manual)
- [ ] Alerts via Telegram when a topic score exceeds threshold (urgent content opportunity)
- [ ] Competitor content monitoring — track what's going viral in the niche
- [ ] Seasonal content calendar — pre-plan around longevity conference season, New Year health spikes, etc.
- [ ] A/B hook testing — post two hook variants, track which performs better, feed result back to Hook Tester

---

## Phase 8 — Audience & Community Scale 🔜 Future

Build the community, not just the content.

- [ ] Instagram comment monitoring via API — inbound comments automatically queued for Community Manager
- [ ] DM response drafts for common questions (peptide sourcing, dosing questions, study requests)
- [ ] Follower milestone celebrations — auto-generate celebration posts at 1k, 5k, 10k
- [ ] Community question collection — pull recurring questions from comments as content ideas
- [ ] Collaboration detection — identify accounts for potential partnerships

---

## Metric Goals

| Metric | Current | 3-Month Target | 6-Month Target |
|---|---|---|---|
| Posts per week | 1–2 (manual) | 3–4 (semi-auto) | 5–7 (fully scheduled) |
| Carousel production time | ~2 hours | ~30 minutes | ~10 minutes |
| Platforms per post | 1 (Instagram) | 3 (IG + Twitter + LinkedIn) | 4 (+ Reels) |
| Manual steps per post | ~6 | ~2 | ~0 |

---

## Priority Order

| Priority | Phase | Unlock |
|---|---|---|
| 1 | Phase 3 — Image Automation | Fully automated carousels |
| 2 | Phase 4 — Scheduling | Hands-free posting |
| 3 | Phase 5 — Analytics Feedback | Self-improving content strategy |
| 4 | Phase 6 — Multi-Platform | 4x reach per piece of content |
| 5 | Phase 7 — Growth Intelligence | Proactive trend capitalisation |
| 6 | Phase 8 — Community Scale | Audience relationship at scale |
