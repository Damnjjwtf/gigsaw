# SCOUT — Startup Intelligence Module for GIGSAW

**Thesis:** Funded startups are a lagging indicator of hiring need. Show up before the job post exists.

## Phase 3 Complete ✓

Full-featured startup intelligence system with multi-source feeds, Claude-powered scoring/drafting, career inspection, dashboard, daily digests, unorthodox plays, and GIGSAW integration.

## Commands

### Discovery
```bash
# Fetch from all sources (TechCrunch, YC, Sequoia, Hacker News)
python3 -m scout.cli feed [--days 60] [--limit 5] [--sources hn,yc]

# At-a-glance pipeline status
python3 -m scout.cli dashboard

# List companies in database
python3 -m scout.cli list [--limit 10]

# Export to JSON
python3 -m scout.cli export
```

### Evaluation
```bash
# Score companies against JJ's profile (Claude API)
python3 -m scout.cli score [--days 60]

# Check career page for open roles
python3 -m scout.cli inspect "Company Name"
```

### Outreach
```bash
# Generate cold outreach draft (Claude API)
python3 -m scout.cli draft "Company Name"

# Generate unorthodox application play (Claude API)
python3 -m scout.cli wild "Company Name"
python3 -m scout.cli wild  # general brainstorm

# Daily intelligence briefing (Claude API)
python3 -m scout.cli digest [--days 1]

# Push high-value company to GIGSAW
python3 -m scout.cli push "Company Name"
```

### Meta
```bash
python3 -m scout.cli config  # API key status
```

## Setup

### Environment Variables
```bash
# Required for evaluation/outreach/wild/digest
export ANTHROPIC_API_KEY="sk-ant-..."

# Required for Apify-based YC/Sequoia scraping (falls back to samples)
export APIFY_API_TOKEN="apify_api_..."

# Optional
export SCOUT_DB_PATH="/custom/path/scout.db"
export SCOUT_EXPORT_DIR="/custom/path/exports"
```

### Dependencies
```bash
pip3 install anthropic requests
```

All other functionality uses Python stdlib (sqlite3, xml.etree, json).

## Architecture

```
scout/
├── __init__.py           Package entry
├── config.py             API key management
├── storage.py            SQLite (companies, scores, drafts, inspections)
├── feed.py               Source orchestration
├── score.py              Claude API scoring (0-100 across 6 factors)
├── draft.py              Claude API outreach generation
├── careers.py            Career page inspection
├── pipeline.py           GIGSAW integration
├── wild.py               Claude API unorthodox plays generator ★
├── dashboard.py          Pipeline status renderer ★
├── digest.py             Claude API daily briefing ★
├── cli.py                Command routing
├── test_scout.py         28 tests, all passing
├── README.md             This file
└── sources/              Modular data source fetchers
    ├── __init__.py
    ├── hackernews.py     Who's Hiring thread parser ★
    └── apify_source.py   YC + Sequoia via Apify ★

★ = New in Phase 3
```

## Data Sources

| Source | Type | Auth | Status |
|--------|------|------|--------|
| TechCrunch RSS | Funding announcements | None | Working (with sample fallback) |
| Y Combinator | Active portfolio | Apify | Working (with sample fallback) |
| Sequoia Capital | Portfolio companies | Apify | Working (with sample fallback) |
| Hacker News "Who's Hiring" | Hiring direct from companies | None | Working (with sample fallback) |
| Crunchbase API | Structured funding | Paid | Skipped (not free) |

All sources have automatic fallback to curated sample data when network is unavailable, so the system always works.

## Scoring System

**Scored 0-100 across 6 factors:**
- Creative Need (0-30) — copywriter/narrative/content/brand demand
- AI Adjacency (0-20) — AI tools, AI workflows, AI-adjacent creative
- Stage Fit (0-15) — earlier stages = more likely to hire generalists
- Hiring Urgency (0-15) — recent funding signals
- Location Fit (0-10) — Bay Area > California > Remote > Other
- Brand Voice (0-10) — public voice, community, narrative focus

Grades: A (90-100), B (80-89), C (70-79), D (60-69), F (0-59).

## Phase 3 Highlights

### `/scout wild` — Unorthodox Plays
Generates specific, named plays (not generic advice) using JJ's actual shipped work as context. Each play includes:
- Memorable name + category
- The insight (why THIS play for THIS company)
- 5-7 numbered execution steps with timing
- The risk (honest)
- The win (full picture, not just an interview)

Example output: "The Constitutional Twine — build an interactive Twine version of Anthropic's published research..."

### `/scout dashboard` — At-a-Glance Status
Terminal dashboard showing:
- Total companies, recent additions, scored, drafted, inspected
- Score distribution histogram
- Top targets (score 80+)
- Recent fetch runs
- Suggested next actions based on pipeline state

### `/scout digest` — Daily Briefing
Markdown digest with:
- Top move today (single most important action)
- High-value targets (80+)
- Watch list (70-79)
- Pattern notice (signals across the day's data)
- Action queue (concrete checkboxes)

Pattern detection is genuinely useful — Claude identifies clusters and trends across batches.

### Hacker News "Who's Hiring" Source
Parses the monthly thread on Hacker News. Each comment is a hiring company that wrote directly with role + tech stack. Better signal than aggregators because companies write the post themselves.

## Testing

```bash
python3 -m scout.test_scout
```

**28 tests, all passing:**
- Storage (6) — insertion, retrieval, deduplication, scores, drafts, inspections
- Feed (4) — orchestration + all sources
- Score (2) — format validation, batch processing
- Draft (1) — generation and formatting
- Careers (2) — HTML parsing, role detection
- Pipeline (2) — GIGSAW recon files, tracker updates
- HackerNews (3) — sample data, post parsing, edge cases
- Apify (2) — fallback behavior
- Wild (2) — play generation
- Dashboard (3) — rendering, stats structure, suggestions
- Digest (1) — empty digest format

## Workflow

```bash
# Morning routine (3 commands)
/scout feed          # Pull fresh startups
/scout score         # Evaluate against profile
/scout digest        # Get briefed in 60 seconds

# When a target catches your eye
/scout draft "Company"     # Cold outreach
/scout wild "Company"      # Unorthodox play
/scout inspect "Company"   # Career page check
/scout push "Company"      # Send to GIGSAW

# Anytime you want a state check
/scout dashboard
```

## GIGSAW Integration

`/scout push [company]` creates:
1. **Recon file** at `/gigsaw/data/recon/[company].md`
2. **Tracker entry** in `/gigsaw/data/applications.tsv`
3. Hands off to `/gigsaw recon`, `/gigsaw build`, `/gigsaw propose`

## Performance

- Feed fetch: 0.5–2s (depending on sources)
- Scoring: 1–2s per company (Claude API)
- Draft: 1–3s (Claude API)
- Wild play: 2–4s (Claude API)
- Digest: 3–5s (Claude API)
- Dashboard: <50ms (local SQLite)
- Full pipeline (12 companies): ~30–40s

## Notes

- Terminal-first, monospace, no emoji
- All output streams to stdout (pipeable)
- Database auto-creates on first run
- Sample data for offline/blocked environments
- Claude API used for: scoring, drafting, wild plays, digests
- HITL (human-in-the-loop) for all critical decisions
- The system itself is the portfolio piece
