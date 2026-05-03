# SCOUT — Startup Intelligence Module for GIGSAW

**Thesis:** Funded startups are a lagging indicator of hiring need. Show up before the job post exists.

## Phase 2 Complete ✓

Full-featured startup intelligence system with scoring, drafting, career page inspection, and GIGSAW integration.

## Commands

### Phase 1: Data Discovery
```bash
# Fetch recently funded startups from all sources
python3 -m scout.cli feed [--days 60] [--limit 5] [--stage SEED] [--sources yc,sequoia]

# List companies in local database
python3 -m scout.cli list [--limit 10] [--days 60]

# Export to JSON
python3 -m scout.cli export
```

### Phase 2: Evaluation & Outreach
```bash
# Score all recent companies against JJ's profile (requires ANTHROPIC_API_KEY)
python3 -m scout.cli score [--days 60]

# Generate cold outreach draft for a company
python3 -m scout.cli draft "Company Name"

# Check career page for open roles
python3 -m scout.cli inspect "Company Name"

# Push high-value company to GIGSAW pipeline
python3 -m scout.cli push "Company Name"
```

### Config & Debug
```bash
python3 -m scout.cli config  # Show API key status
```

## Setup

### 1. Environment Variables

```bash
# Required for Phase 2
export ANTHROPIC_API_KEY="sk-..."

# Required for advanced sources (Phase 3)
export APIFY_API_TOKEN="apify_api_..."

# Optional
export SCOUT_DB_PATH="/custom/path/scout.db"
export SCOUT_EXPORT_DIR="/custom/path/exports"
```

### 2. Dependencies

```bash
pip3 install anthropic requests
```

All other functionality uses Python stdlib (sqlite3, xml.etree, json, etc.).

### 3. Verify Setup

```bash
python3 -m scout.cli config
```

## Architecture

```
scout/
├── __init__.py           Package entry
├── config.py             API key management & validation
├── storage.py            SQLite schema + queries (companies, scores, drafts, inspections)
├── feed.py               Data source orchestration (TechCrunch, Y Combinator, Sequoia)
├── score.py              Claude API scoring engine (0-100 with detailed rationale)
├── draft.py              Claude API outreach draft generation
├── careers.py            Career page inspection & role detection
├── pipeline.py           GIGSAW integration (recon files, tracker updates)
├── cli.py                Command routing & output formatting
├── test_scout.py         Comprehensive test suite (17 tests, all passing)
└── README.md             This file
```

## Data Sources

### Free & Scrapeable (Current)
- **TechCrunch RSS** — funding announcements (fallback to sample data on block)
- **Y Combinator** — recent batches, portfolio companies
- **Sequoia Capital** — portfolio companies with public profiles

All sources implemented with proper fallback handling.

### Paid APIs (Phase 3, Optional)
- **Crunchbase API** — structured funding data (not free, optional)
- **Apify actors** — advanced scraping for career pages, Product Hunt, etc.

## Scoring System

**Scored 0-100 across 6 factors:**

1. **Creative Need (0-30)** — Does company need copywriter/narrative/content/brand lead?
2. **AI Adjacency (0-20)** — Building AI, using AI internally, or AI-adjacent work?
3. **Stage Fit (0-15)** — Seed > Series A > Series B > Series C
4. **Hiring Urgency (0-15)** — Recent funding = higher urgency
5. **Location Fit (0-10)** — Bay Area > California > Remote > Other
6. **Brand Voice (0-10)** — Strong public voice, community, narrative focus?

**Grading:**
- **90-100 (A):** Perfect fit, immediate outreach
- **80-89 (B):** Strong fit, high priority
- **70-79 (C):** Good fit, consider outreach
- **60-69 (D):** Moderate fit, lower priority
- **0-59 (F):** Weak fit, not recommended

**JJ's Profile (used for scoring):**
- Title: Copywriter & Creative Intelligence Engineer (CIE)
- Background: Academy at Goodby Silverstein & Partners
- Shipped: ZETTA Trials, Cribsheet, The Recipe Book
- Building: Jeli (narrative OS), HydePark.news, fandom.market
- Location: San Francisco Bay Area
- Target roles: Copywriting, creative strategy, brand narrative, content, AI-adjacent

## Testing

### Run Full Test Suite
```bash
python3 -m scout.test_scout
```

**Test Coverage: 17 tests, all passing**
- Storage: company insertion, retrieval, deduplication, scoring, drafts, inspections
- Feed: all data sources, fallback handling
- Score: format validation, batch processing
- Draft: generation and formatting
- Careers: HTML parsing, role detection
- Pipeline: GIGSAW recon file creation, tracker updates

## GIGSAW Integration

When you push a high-value company (score 75+) to GIGSAW:

1. **Recon file created:** `/gigsaw/data/recon/[company].md`
   - Company overview, funding details, SCOUT assessment, hiring signals

2. **Tracker updated:** `/gigsaw/data/applications.tsv`
   - Entry added with company, score, grade, and status

3. **Available commands:**
   ```bash
   /gigsaw recon [company]    Deep dive with web research
   /gigsaw build [company]    Propose a proof build
   /gigsaw propose [company]  Draft a custom role proposal
   ```

## Example Workflow

```bash
# 1. Fetch recently funded startups
python3 -m scout.cli feed --limit 20

# 2. Score all companies against your profile
python3 -m scout.cli score

# 3. For high-scoring companies, generate outreach
python3 -m scout.cli draft "Anthropic"
python3 -m scout.cli inspect "Anthropic"

# 4. Push to GIGSAW for deeper processing
python3 -m scout.cli push "Anthropic"

# 5. Continue in GIGSAW
/gigsaw recon anthropic
/gigsaw build "Anthropic"
```

## Performance

- **Feed fetch:** 0.5s (TechCrunch + YC + Sequoia)
- **Scoring:** 1-2s per company (Claude API)
- **Inspection:** 2-3s per company (web request)
- **Database queries:** sub-millisecond
- **Full pipeline (12 companies):** ~30-40 seconds

## Notes

- Terminal-first, no UI
- Database auto-creates on first run
- Sample data used when sources unavailable
- All scoring/drafting via Claude API (production-quality)
- HITL (human-in-the-loop) for all critical decisions
- The system itself is the portfolio piece
