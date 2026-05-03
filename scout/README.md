# SCOUT — Startup Intelligence Module for GIGSAW

**Thesis:** Funded startups are a lagging indicator of hiring need. Show up before the job post exists.

## MVP Status

✓ Config management with API key validation
✓ SQLite persistence (companies, runs, scores)
✓ TechCrunch RSS parser (with fallback sample data)
✓ Terminal CLI with clean output formatting
✓ Sample data for demo/testing

## Commands

```bash
# Fetch recent startups
python3 -m scout.cli feed [--days 60] [--limit 5] [--stage SEED]

# List companies in database
python3 -m scout.cli list [--limit 10] [--days 60]

# Check configuration
python3 -m scout.cli config

# Export to JSON
python3 -m scout.cli export
```

## Setup

1. **No dependencies required for MVP** — uses Python stdlib + requests (already available)

2. **Optional: Set API keys for future phases**
   ```bash
   export ANTHROPIC_API_KEY="sk-..."
   export CRUNCHBASE_API_KEY="your_key"
   export APIFY_API_TOKEN="your_token"
   ```

3. **Run MVP test**
   ```bash
   python3 -m scout.cli feed --limit 5
   ```

## Architecture

```
scout/
├── __init__.py          Package entry point
├── config.py            API key loading + validation
├── storage.py           SQLite schema + queries
├── feed.py              Data source orchestration
├── cli.py               Command router
└── README.md            This file
```

## Data Sources (Roadmap)

### Phase 1 ✓ (MVP)
- **TechCrunch RSS** — funding announcements (fallback: sample data)

### Phase 2 (In Progress)
- Crunchbase API — structured funding data
- Y Combinator scraper — recent batches
- Sequoia Capital scraper — portfolio companies

### Phase 3
- Career page checking via Apify
- Scoring against profile.json via Claude API
- Cold outreach draft generation
- GIGSAW pipeline integration

## TechCrunch Feed Issue

TechCrunch blocks automated requests (403 Forbidden). For production use:

**Option A:** Use Crunchbase API (Phase 2)
**Option B:** Use Apify actor for scraping (requires API token)
**Option C:** Add your own data sources (JSON file, database, etc.)

For MVP, sample data is used as fallback.

## Data Format

Each company in the feed:

```json
{
  "name": "Company Name",
  "stage": "Series A",
  "amount_usd": 5000000,
  "announced_date": "2024-05-03T00:00:00",
  "source": "techcrunch",
  "description": "What they do",
  "website": "https://...",
  "investors": ["Investor 1", "Investor 2"]
}
```

## Next Steps

1. Implement Crunchbase API integration
2. Add company scoring against JJ's profile
3. Generate cold outreach drafts via Claude API
4. Integrate with main GIGSAW pipeline (`/gigsaw push`)

## Notes

- Keep it fast — stream output as it comes
- Monospace terminal aesthetic — no emoji
- HITL (human-in-the-loop) for all critical decisions
- The system itself is the portfolio piece
