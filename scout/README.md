# SCOUT — Startup Intelligence Module for GIGSAW

**Thesis:** Funded startups are a lagging indicator of hiring need. Show up before the job post exists.

## Phase 4 Complete ✓

The complete intelligence-arbitrage system. Every command from CLAUDE.md, fully implemented and tested.

## Commands

### Discovery
```bash
/scout feed              # Fetch from all sources (TechCrunch, YC, Sequoia, HN)
/scout dashboard         # At-a-glance pipeline status
/scout list              # Browse database
/scout export            # JSON export
```

### Evaluation
```bash
/scout score             # Score companies against JJ's profile (Claude API)
/scout recon [company]   # Deep company research brief (★ Phase 4)
/scout arbitrage [co]    # Read role as lagging indicator (★★ core differentiator)
/scout inspect [company] # Career page check
```

### Outreach
```bash
/scout draft [company]      # Cold outreach draft
/scout propose [company]    # Write the role they haven't posted (★★ core differentiator)
/scout remix [co] [role]    # Tailored resume + cover + portfolio (★ Phase 4)
/scout wild [company]       # Unorthodox application play
/scout who [company]        # LinkedIn warm paths (★ Phase 4)
/scout digest               # Daily intelligence briefing
/scout push [company]       # Send to GIGSAW pipeline
```

### Automation (★ Phase 4)
```bash
/scout watch                          # Run pipeline loop (every 60min)
/scout watch --once                   # Run pipeline cycle once
/scout watch --install-cron daily     # Generate cron line
/scout watch --install-launchd        # Generate macOS launchd plist
/scout alerts                         # Show alert configuration status
```

### Meta
```bash
/scout config            # API key status
```

## Setup

### Environment Variables

```bash
# Required for Claude-powered features
export ANTHROPIC_API_KEY="sk-ant-..."

# Required for Apify-based YC/Sequoia scraping (falls back to samples)
export APIFY_API_TOKEN="apify_api_..."

# Optional: alert webhooks
export SLACK_WEBHOOK_URL="https://hooks.slack.com/..."
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
export ALERT_EMAIL="you@example.com"

# Optional: paths
export SCOUT_DB_PATH="/custom/scout.db"
export SCOUT_EXPORT_DIR="/custom/exports"
```

### Dependencies
```bash
pip3 install anthropic requests
```

## Architecture

```
scout/
├── __init__.py
├── config.py                 API key management
├── storage.py                SQLite (companies, scores, drafts, inspections)
├── feed.py                   Source orchestration
├── score.py                  Claude scoring (0-100 across 6 factors)
├── draft.py                  Cold outreach generation
├── careers.py                Career page inspection
├── pipeline.py               GIGSAW integration
├── wild.py                   Unorthodox plays generator
├── dashboard.py              Pipeline status renderer
├── digest.py                 Daily Claude briefings
├── arbitrage.py              ★ Intelligence Arbitrage Engine (Phase 4)
├── propose.py                ★ Role Proposal Generator (Phase 4)
├── who.py                    ★ LinkedIn warm-path finder (Phase 4)
├── recon.py                  ★ Deep company research (Phase 4)
├── watch.py                  ★ Background scheduler (Phase 4)
├── alerts.py                 ★ Multi-channel alerts (Phase 4)
├── remix.py                  ★ Application package generator (Phase 4)
├── cli.py                    Command routing
├── test_scout.py             40 tests, all passing
├── README.md                 This file
└── sources/
    ├── hackernews.py         HN Who's Hiring parser
    └── apify_source.py       YC + Sequoia via Apify
```

## The Five Phase 4 Differentiators

### 1. `/scout arbitrage` — Intelligence Arbitrage Engine ★★

The single most important command. Reads job descriptions as lagging indicators and identifies what the role is BECOMING in the next 12-18 months as AI capabilities reshape it. Output:

- **ROLE AS WRITTEN** — what the JD says
- **ROLE AS BECOMING** — what it will be
- **THE GAP** — what the company doesn't know they need yet
- **JJ'S POSITION IN THE GAP** — why he's already doing the future version
- **INTERVIEW REFRAME** — how to talk about the role
- **PROOF BUILD SUGGESTION** — what to ship
- **CONFIDENCE** — high/medium/low — honest read on whether the role will actually transform

### 2. `/scout propose` — Role Proposal Generator ★★

For companies that don't have the right posted role. Identifies the role they're SPLITTING across multiple hires because they don't have the category yet. Writes a 500-word proposal that:

- Demonstrates genuine insight about THEIR specific posting pattern
- Proposes a real-sounding title, function, and reporting line
- Lists 3-5 concrete outputs (not vague responsibilities)
- Backs every claim with a shipped project URL
- Ends with a specific, low-friction next step

### 3. `/scout who` — Network Cross-Reference ★

Greps `data/connections.csv` (LinkedIn export) for matches at a target company. When matches exist, optionally generates personalized warm-intro messages via Claude. When no matches, recommends `/scout wild` for differentiation.

```bash
/scout who "Anthropic"          # List connections
/scout who "Anthropic" --draft  # + generate warm-intro DMs
```

### 4. `/scout recon` — Deep Research ★

Synthesizes everything we know about a target (database + scores + drafts + inspections) into a recon brief covering:

- Snapshot, why they matter to JJ
- Public-facing gaps (build/proposal opportunities)
- Hiring pattern, AI posture
- The build angle, the proposal angle, the wild play
- Verdict: Build / Propose / Apply / Skip / Watch

### 5. `/scout remix` — Tailored Application Package ★

Generates 4 files in `output/[company]_[role]/`:

- `resume.md` — proof builds foregrounded, experience reordered for relevance
- `cover-letter.md` — reads like a builder's letter, not an applicant's plea
- `portfolio-selection.md` — top 3 projects picked for THIS target
- `match-assessment.json` — fit score, strongest signals, honest gaps, recommendation

## Live Output Examples

### `/scout arbitrage "Anthropic"`
```
## ROLE AS BECOMING (12-18 months)
Anthropic's creative and brand functions are shifting from "explain
what Claude does" to "demonstrate what Claude *enables*" through
interactive artifacts, not static decks or blog posts. Expect
Claude-native marketing: Artifacts-as-campaigns, agentic demos,
prompt-driven narrative experiences...

## THE GAP
Anthropic has world-class researchers and policy writers, but a
thin layer of people who can translate model capabilities into
emotionally resonant, narrative-driven artifacts that non-technical
audiences feel.
```

### `/scout propose "Replit"` (excerpt)
```
## The Pattern I Noticed
Replit's pivot to "Agent" — natural-language app building for
non-coders — broke your old copy model. Your docs team writes for
developers, your marketing team writes for prosumers, and your
DevRel team demos to founders. Three audiences, three voices, one
product surface. Meanwhile, the Agent itself is generating UI copy,
error messages, and onboarding flows on behalf of users who can't
write them...

## The Role That's Missing
**Title:** Staff Writer, Agent Experience
**Reports To:** Head of Product (dotted line to Design)
```

### `/scout recon "Anthropic"` (excerpt)
```
## The Build Angle
Ship a public artifact that documents Claude's voice the way a
brand bible documents a character — annotated transcripts, voice
principles reverse-engineered from outputs, a "Claude Style Guide"
written from the outside.

## Verdict
**Recommended Action:** Build (then Apply)
**Reasoning:** Anthropic is a long-shot direct-apply for a
non-pedigreed candidate, but it's the single best match for JJ's
CIE thesis in the entire frontier-lab tier.
```

## Automation

### Run Once Manually
```bash
/scout watch --once
```

### Daily Cron Install
```bash
# Generate the cron line
/scout watch --install-cron daily

# Edit your crontab and paste it
crontab -e
```

### macOS launchd Install
```bash
# Generate the plist
/scout watch --install-launchd > ~/Library/LaunchAgents/com.gigsaw.scout.watch.plist

# Load it
launchctl load ~/Library/LaunchAgents/com.gigsaw.scout.watch.plist
```

### Alerts on High-Value Matches

Pipeline runs automatically score companies. Any company scoring 80+ triggers:
- File log: `data/alerts/alerts_YYYYMMDD.log`
- Slack (if `SLACK_WEBHOOK_URL` set)
- Discord (if `DISCORD_WEBHOOK_URL` set)
- Email queue (if `ALERT_EMAIL` set)

## Testing

```bash
python3 -m scout.test_scout
```

**40 tests, all passing:**

| Module | Tests |
|--------|-------|
| Storage | 6 |
| Feed | 4 |
| Score | 2 |
| Draft | 1 |
| Careers | 2 |
| Pipeline | 2 |
| HackerNews | 3 |
| Apify | 2 |
| Wild | 2 |
| Dashboard | 3 |
| Digest | 1 |
| **Arbitrage** | **1** ★ |
| **Propose** | **1** ★ |
| **NetworkScanner** | **2** ★ |
| **Recon** | **1** ★ |
| **Watcher** | **2** ★ |
| **AlertSystem** | **3** ★ |
| **Remix** | **2** ★ |
| **TOTAL** | **40** |

## Workflow

### Morning Routine (3 commands)
```bash
/scout feed              # Fresh data
/scout score             # Evaluate
/scout digest            # Get briefed
```

### When a Target Catches Your Eye
```bash
/scout recon "Co"        # Full intel brief
/scout arbitrage "Co"    # What the role is becoming
/scout who "Co"          # Warm paths first
```

### Decide Move
- **Build** → ship a proof artifact (custom for the company)
- **Propose** → `/scout propose "Co"` writes the missing role
- **Apply** → `/scout remix "Co" "Role"` generates package
- **Wild** → `/scout wild "Co"` for unorthodox plays
- **Watch** → keep monitoring, defer action

### Send
```bash
/scout draft "Co"        # Cold outreach if no warm path
/scout push "Co"         # Track in GIGSAW pipeline
```

## GIGSAW Integration

`/scout push` creates:
- **Recon file** → `/gigsaw/data/recon/[company].md`
- **Tracker entry** → `/gigsaw/data/applications.tsv`
- Hands off to `/gigsaw recon`, `/gigsaw build`, `/gigsaw propose`

`/scout remix` outputs to `/gigsaw/output/[company]_[role]/` matching GIGSAW's expected structure.

## Performance

| Operation | Time |
|-----------|------|
| Feed fetch | 0.5–2s |
| Scoring | 1–2s per company |
| Draft | 1–3s |
| Wild play | 2–4s |
| Digest | 3–5s |
| Arbitrage | 3–5s |
| Propose | 3–5s |
| Recon | 4–6s |
| Remix | 8–12s (4 Claude calls) |
| Dashboard | <50ms (local SQLite) |

## Notes

- Terminal-first, monospace, no emoji
- All sources have automatic sample-data fallback
- Database auto-creates on first run
- HITL (human-in-the-loop) for all critical decisions
- Every Phase 4 differentiator is implemented per CLAUDE.md spec
- The system itself is the portfolio piece
