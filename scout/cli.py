#!/usr/bin/env python3

import sys
import json
from datetime import datetime
from scout.config import Config
from scout.feed import Feed
from scout.storage import ScoutStorage
from scout.score import ScoreEngine
from scout.draft import DraftEngine
from scout.careers import CareerPageInspector
from scout.pipeline import GigsawPipeline


def format_amount(amount_usd):
    """Format USD amount as human-readable string."""
    if amount_usd >= 1_000_000_000:
        return f'${amount_usd / 1_000_000_000:.1f}B'
    elif amount_usd >= 1_000_000:
        return f'${amount_usd / 1_000_000:.1f}M'
    elif amount_usd >= 1_000:
        return f'${amount_usd / 1_000:.1f}K'
    else:
        return f'${amount_usd}'


def format_date(iso_date):
    """Convert ISO date to relative day format."""
    try:
        dt = datetime.fromisoformat(iso_date)
        days_ago = (datetime.now() - dt).days
        if days_ago == 0:
            return 'today'
        elif days_ago == 1:
            return 'yesterday'
        else:
            return f'{days_ago}d ago'
    except:
        return iso_date


def cmd_feed(days=60, limit=5, stage=None, sources=None):
    """Fetch and display recently funded startups."""
    print(f'\n--- SCOUT FEED ---')

    # Validate config first
    if not Config.check():
        pass  # Continue anyway, TechCrunch doesn't need keys

    # Fetch from enabled sources
    feed = Feed()
    if sources:
        sources = sources.split(',')
    else:
        sources = ['techcrunch', 'yc', 'sequoia']

    companies = feed.fetch_all(days=days, sources=sources)

    if not companies:
        print('✗ No companies fetched')
        return 1

    # Filter by stage if specified
    if stage:
        companies = [c for c in companies if c.get('stage', '').lower() == stage.lower()]

    # Save to storage
    new_count = feed.save_feed(companies)
    print(f'✓ Stored: {new_count} new companies')

    # Display results
    print(f'\n--- TOP {min(limit, len(companies))} RESULTS ---\n')

    for i, company in enumerate(companies[:limit]):
        company_name = company.get('name', 'Unknown')
        stage_val = company.get('stage', 'unknown')
        amount = format_amount(company.get('amount_usd', 0))
        date_str = format_date(company.get('announced_date', ''))

        print(f'{company_name:30} [{stage_val:10}] {amount:12} {date_str:12}')
        if company.get('description'):
            desc = company['description'][:80].replace('\n', ' ')
            print(f'  {desc}')
        print()

    print(f'---\n')
    return 0


def cmd_score(days=60, min_score=75):
    """Score all recent companies against JJ's profile."""
    print(f'\n--- SCOUT SCORE ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set — scoring requires Claude API')
        return 1

    storage = ScoutStorage()
    companies = storage.get_recent_companies(days=days)

    if not companies:
        print('✗ No companies to score')
        return 1

    print(f'Scoring {len(companies)} companies...\n')

    scorer = ScoreEngine()
    results = scorer.score_batch(companies, min_score=min_score)

    if not results:
        print(f'✗ No companies scored above {min_score}')
        return 1

    print(f'\n--- HIGH-VALUE TARGETS ({len(results)} companies scoring {min_score}+) ---\n')

    for company in results:
        print(scorer.format_score_report(company))

    return 0


def cmd_draft(company_name=None):
    """Generate cold outreach draft for a company."""
    print(f'\n--- SCOUT DRAFT ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set')
        return 1

    if not company_name:
        print('✗ Specify company name: /scout draft "Company Name"')
        return 1

    storage = ScoutStorage()
    company = storage.get_company(company_name)

    if not company:
        print(f'✗ Company not found: {company_name}')
        return 1

    # Get score if available
    score_result = None
    try:
        conn = __import__('sqlite3').connect(Config.DB_PATH)
        conn.row_factory = __import__('sqlite3').Row
        row = conn.execute(
            'SELECT * FROM scores WHERE company_name = ? ORDER BY timestamp DESC LIMIT 1',
            (company_name,)
        ).fetchone()
        if row:
            score_result = dict(row)
        conn.close()
    except:
        pass

    # Generate draft
    drafter = DraftEngine()
    draft = drafter.generate_draft(company, score_result)

    print(f'\nCompany: {company_name}')
    print(f'Funding: ${company.get("amount_usd", 0):,} | Stage: {company.get("stage")}')
    print(f'\n{drafter.format_draft(company_name, draft)}')

    return 0


def cmd_inspect(company_name=None):
    """Inspect company career page for open roles."""
    print(f'\n--- SCOUT INSPECT ---')

    if not company_name:
        print('✗ Specify company name: /scout inspect "Company Name"')
        return 1

    storage = ScoutStorage()
    company = storage.get_company(company_name)

    if not company:
        print(f'✗ Company not found: {company_name}')
        return 1

    inspector = CareerPageInspector()
    result = inspector.inspect_company(company)

    if result.get('open_roles'):
        print(f'\n✓ Found {len(result["open_roles"])} roles')
        print(f'Hiring Urgency: {result.get("hiring_urgency", "unknown")}')
        print(f'Roles: {", ".join(result["open_roles"])}')
    else:
        print(f'\n○ No career page or roles detected')

    return 0


def cmd_push(company_name=None):
    """Push a high-value company to GIGSAW pipeline."""
    print(f'\n--- SCOUT PUSH ---')

    if not company_name:
        print('✗ Specify company name: /scout push "Company Name"')
        return 1

    storage = ScoutStorage()
    company = storage.get_company(company_name)

    if not company:
        print(f'✗ Company not found: {company_name}')
        return 1

    # Get score if available
    score_result = None
    try:
        conn = __import__('sqlite3').connect(Config.DB_PATH)
        conn.row_factory = __import__('sqlite3').Row
        row = conn.execute(
            'SELECT * FROM scores WHERE company_name = ? ORDER BY timestamp DESC LIMIT 1',
            (company_name,)
        ).fetchone()
        if row:
            score_result = dict(row)
        conn.close()
    except:
        pass

    if not score_result or score_result.get('score', 0) < 75:
        print(f'✗ Company score is below 75 ({score_result.get("score", 0) if score_result else 0})')
        print('  Use /scout score first, or push manually with /gigsaw recon')
        return 1

    # Get inspection if available
    inspection = storage.get_inspection(company_name)

    # Get draft if available
    draft = storage.get_draft(company_name)

    # Push to GIGSAW
    pipeline = GigsawPipeline()
    success = pipeline.push_company(company, score_result, draft, inspection)

    if success:
        print(f'\n✓ {company_name} pushed to GIGSAW')
        print(f'  Score: {score_result.get("score")}/100')
        print(f'  Next: /gigsaw recon {company_name.lower().replace(" ", "_")}')
    else:
        print(f'✗ Push failed')

    return 0


def cmd_config_check():
    """Check and display configuration status."""
    Config.status()
    Config.check()
    return 0


def cmd_list(limit=10, days=60):
    """List companies in database."""
    storage = ScoutStorage()
    companies = storage.get_recent_companies(days=days)

    if not companies:
        print('✗ No companies in database')
        return 1

    print(f'\n--- DATABASE ({len(companies)} RECENT) ---\n')
    for company in companies[:limit]:
        company_name = company['name']
        stage = company['stage']
        amount = format_amount(company['amount_usd']) if company['amount_usd'] else 'N/A'
        date_str = format_date(company['announced_date'])

        print(f'{company_name:30} [{stage:10}] {amount:12} {date_str:12}')

    print(f'\n---\n')
    return 0


def cmd_export(format='json'):
    """Export companies to file."""
    storage = ScoutStorage()
    companies = storage.get_all_companies()

    if not companies:
        print('✗ No companies to export')
        return 1

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'{Config.EXPORT_DIR}/scout_export_{timestamp}.{format}'

    if format == 'json':
        with open(output_file, 'w') as f:
            json.dump(companies, f, indent=2)

    print(f'✓ Exported {len(companies)} companies to {output_file}')
    return 0


def main():
    """Command router."""
    if len(sys.argv) < 2:
        print('Usage: /scout <command> [options]')
        print('\nPhase 1 Commands:')
        print('  feed           Fetch recent startups from all sources')
        print('  list           List companies in database')
        print('  config         Check configuration status')
        print('  export         Export companies to JSON')
        print('\nPhase 2 Commands:')
        print('  score          Score companies against JJ\'s profile')
        print('  draft [name]   Generate cold outreach draft')
        print('  inspect [name] Check career page for open roles')
        print('  push [name]    Push to GIGSAW pipeline')
        print('\nOptions:')
        print('  --days N       Set recency window (default: 60)')
        print('  --limit N      Limit results (default: 5)')
        print('  --stage SEED   Filter by funding stage')
        print('  --sources yc,sequoia  Comma-separated sources')
        return 0

    command = sys.argv[1]

    # Parse options
    days = 60
    limit = 5
    stage = None
    sources = None
    for i, arg in enumerate(sys.argv[2:]):
        if arg == '--days' and i + 2 < len(sys.argv):
            days = int(sys.argv[i + 3])
        elif arg == '--limit' and i + 2 < len(sys.argv):
            limit = int(sys.argv[i + 3])
        elif arg == '--stage' and i + 2 < len(sys.argv):
            stage = sys.argv[i + 3]
        elif arg == '--sources' and i + 2 < len(sys.argv):
            sources = sys.argv[i + 3]

    # Route commands
    if command == 'feed':
        return cmd_feed(days=days, limit=limit, stage=stage, sources=sources)
    elif command == 'score':
        return cmd_score(days=days)
    elif command == 'draft':
        company = sys.argv[2] if len(sys.argv) > 2 else None
        return cmd_draft(company)
    elif command == 'inspect':
        company = sys.argv[2] if len(sys.argv) > 2 else None
        return cmd_inspect(company)
    elif command == 'push':
        company = sys.argv[2] if len(sys.argv) > 2 else None
        return cmd_push(company)
    elif command == 'list':
        return cmd_list(limit=limit, days=days)
    elif command == 'config':
        return cmd_config_check()
    elif command == 'export':
        return cmd_export()
    else:
        print(f'✗ Unknown command: {command}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
