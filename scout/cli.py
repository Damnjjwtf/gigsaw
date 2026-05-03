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
from scout.wild import WildEngine
from scout.dashboard import Dashboard
from scout.digest import DigestGenerator
from scout.arbitrage import ArbitrageEngine
from scout.propose import ProposeEngine
from scout.who import NetworkScanner
from scout.recon import ReconEngine
from scout.watch import Watcher
from scout.alerts import AlertSystem
from scout.remix import RemixEngine


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


def cmd_wild(target=None):
    """Generate an unorthodox application play."""
    print(f'\n--- SCOUT WILD ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set')
        return 1

    engine = WildEngine()

    if target:
        print(f'Generating wild play for: {target}\n')
    else:
        print('Generating fresh wild play\n')

    play = engine.generate_play(target=target)
    print(play)
    print('\n---\n')
    return 0


def cmd_dashboard():
    """Render the pipeline dashboard."""
    dashboard = Dashboard()
    print(dashboard.render())
    return 0


def cmd_digest(days=1):
    """Generate a daily digest of recent high-value targets."""
    print(f'\n--- SCOUT DIGEST ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set')
        return 1

    generator = DigestGenerator()
    digest = generator.generate(days=days)
    print()
    print(digest)
    print('\n---\n')
    return 0


def cmd_arbitrage(input_arg=None):
    """Run intelligence arbitrage analysis on a job description or company."""
    print(f'\n--- SCOUT ARBITRAGE ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set')
        return 1

    if not input_arg:
        print('✗ Specify a company name or paste a job description')
        print('  Usage: /scout arbitrage "Company Name"')
        print('  Or pipe text: cat job.txt | /scout arbitrage -')
        return 1

    # Allow piping job text via "-"
    if input_arg == '-':
        job_text = sys.stdin.read().strip()
        company_name = None
    else:
        company_name = input_arg
        # Pull description from storage
        storage = ScoutStorage()
        company = storage.get_company(company_name)
        if not company:
            print(f'✗ Company "{company_name}" not in database. Run /scout feed first or use - to pipe a JD.')
            return 1
        job_text = company.get('description', '') or ''

    engine = ArbitrageEngine()
    print(f'Analyzing {company_name or "job description"}...\n')
    result = engine.analyze(job_text, company_name=company_name)
    print(result['report'])
    print('\n---\n')
    return 0


def cmd_propose(company_name=None):
    """Generate a role proposal for a company that hasn't posted the right role."""
    print(f'\n--- SCOUT PROPOSE ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set')
        return 1

    if not company_name:
        print('✗ Specify a company: /scout propose "Company Name"')
        return 1

    engine = ProposeEngine()
    print(f'Generating role proposal for {company_name}...\n')
    result = engine.generate_proposal(company_name)
    print(result['proposal'])
    if result.get('saved_to'):
        print(f'\nSaved to: {result["saved_to"]}')
    print('\n---\n')
    return 0


def cmd_who(company_name=None, draft=False):
    """Cross-reference LinkedIn connections for warm paths into a company."""
    print(f'\n--- SCOUT WHO ---')

    if not company_name:
        print('✗ Specify a company: /scout who "Company Name"')
        return 1

    scanner = NetworkScanner()
    print(scanner.report(company_name, generate_drafts=draft))
    return 0


def cmd_recon(company_name=None):
    """Generate a deep recon brief for a company."""
    print(f'\n--- SCOUT RECON ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set')
        return 1

    if not company_name:
        print('✗ Specify a company: /scout recon "Company Name"')
        return 1

    engine = ReconEngine()
    print(f'Researching {company_name}...\n')
    result = engine.deep_dive(company_name)
    print(result['report'])
    if result.get('saved_to'):
        print(f'\nSaved to: {result["saved_to"]}')
    print('\n---\n')
    return 0


def cmd_watch(once=False, interval=60, install_cron=None, install_launchd=False):
    """Run pipeline on a schedule, or install as cron/launchd."""
    print(f'\n--- SCOUT WATCH ---')

    watcher = Watcher()

    if install_cron:
        line = watcher.install_cron(frequency=install_cron)
        print('Add this line to your crontab (run `crontab -e`):\n')
        print(line)
        print('\nOr save to a file: scout/install/scout.cron\n')
        return 0

    if install_launchd:
        plist = watcher.install_launchd()
        print('Save this as ~/Library/LaunchAgents/com.gigsaw.scout.watch.plist:\n')
        print(plist)
        print('\nThen run: launchctl load ~/Library/LaunchAgents/com.gigsaw.scout.watch.plist\n')
        return 0

    if once:
        summary = watcher.run_once()
        print(f'\n✓ Pipeline cycle complete')
        print(f'  Fetched: {summary["fetched"]}')
        print(f'  New: {summary["new"]}')
        print(f'  Scored: {summary["scored"]}')
        print(f'  High-value: {summary["high_value"]}')
        print(f'  Alerts sent: {summary["alerts_sent"]}')
        print(f'  Elapsed: {summary["elapsed_seconds"]:.1f}s')
        if summary['errors']:
            print(f'  Errors: {", ".join(summary["errors"])}')
        return 0

    # Run as daemon loop
    print(f'Starting watch loop (every {interval}m). Press Ctrl+C to stop.\n')
    watcher.loop(interval_minutes=interval)
    return 0


def cmd_alerts():
    """Show alert configuration status."""
    print('\n--- SCOUT ALERTS ---')
    alerts = AlertSystem()
    status = alerts.status()
    print(f'  Slack:    {"✓ configured" if status["slack"] else "○ set SLACK_WEBHOOK_URL"}')
    print(f'  Discord:  {"✓ configured" if status["discord"] else "○ set DISCORD_WEBHOOK_URL"}')
    print(f'  Email:    {"✓ configured" if status["email"] else "○ set ALERT_EMAIL"}')
    print(f'  File log: ✓ always on (data/alerts/)')
    print()
    return 0


def cmd_remix(company_name=None, role=None):
    """Generate tailored application package: resume, cover, portfolio."""
    print(f'\n--- SCOUT REMIX ---')

    if not Config.ANTHROPIC_API_KEY:
        print('✗ ANTHROPIC_API_KEY not set')
        return 1

    if not company_name:
        print('✗ Specify a company: /scout remix "Company Name" [Role]')
        return 1

    engine = RemixEngine()
    print(f'Generating application package for {company_name}'
          + (f' / {role}' if role else '') + '...\n')
    result = engine.remix(company_name, role=role)

    if result.get('success'):
        print(f'✓ Package generated at: {result["output_dir"]}')
        print('  Files:')
        for f in result.get('files', []):
            print(f'    - {f}')
        print('\n  Review carefully before sending. Edit anything that doesn\'t feel right.\n')
    else:
        print(f'✗ {result.get("error", "Unknown error")}')
    return 0


def cmd_serve(host='127.0.0.1', port=8000):
    """Start the SCOUT web dashboard."""
    from scout.web import serve
    serve(host=host, port=port)
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
        print('\nDISCOVERY:')
        print('  feed              Fetch recent startups from all sources')
        print('  list              List companies in database')
        print('  dashboard         At-a-glance pipeline status')
        print('  export            Export companies to JSON')
        print('\nEVALUATION:')
        print('  score             Score companies against JJ\'s profile')
        print('  recon [name]      Deep company research brief')
        print('  arbitrage [name]  Read role as lagging indicator (★ core differentiator)')
        print('  inspect [name]    Check career page for open roles')
        print('\nOUTREACH:')
        print('  draft [name]      Generate cold outreach draft')
        print('  propose [name]    Write the role they haven\'t posted yet (★)')
        print('  remix [name]      Tailored resume + cover + portfolio (★)')
        print('  wild [name]       Generate unorthodox application play')
        print('  who [name]        Find warm paths via LinkedIn connections (★)')
        print('  digest            Daily intelligence briefing')
        print('  push [name]       Push to GIGSAW pipeline')
        print('\nAUTOMATION:')
        print('  watch [--once]    Run pipeline cycle (or --install-cron daily)')
        print('  alerts            Alert channel configuration status')
        print('  serve             Start web dashboard at http://127.0.0.1:8000')
        print('\nMETA:')
        print('  config            Check API key configuration')
        print('\nOptions:')
        print('  --days N          Set recency window (default: 60)')
        print('  --limit N         Limit results (default: 5)')
        print('  --stage SEED      Filter by funding stage')
        print('  --sources hn,yc   Comma-separated: techcrunch,yc,sequoia,hackernews')
        print('  --draft           Generate warm outreach draft (with /scout who)')
        print('  --interval N      Watch interval in minutes (default: 60)')
        print('  --host HOST       Bind host for serve (default: 127.0.0.1)')
        print('  --port PORT       Bind port for serve (default: 8000)')
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
    elif command == 'wild':
        target = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
        return cmd_wild(target)
    elif command == 'dashboard':
        return cmd_dashboard()
    elif command == 'digest':
        return cmd_digest(days=days)
    elif command == 'arbitrage':
        target = sys.argv[2] if len(sys.argv) > 2 else None
        return cmd_arbitrage(target)
    elif command == 'propose':
        target = sys.argv[2] if len(sys.argv) > 2 else None
        return cmd_propose(target)
    elif command == 'who':
        target = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
        draft = '--draft' in sys.argv
        return cmd_who(target, draft=draft)
    elif command == 'recon':
        target = sys.argv[2] if len(sys.argv) > 2 else None
        return cmd_recon(target)
    elif command == 'watch':
        once = '--once' in sys.argv
        install_cron = None
        if '--install-cron' in sys.argv:
            idx = sys.argv.index('--install-cron')
            install_cron = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else 'daily'
        install_launchd = '--install-launchd' in sys.argv
        watch_interval = 60
        if '--interval' in sys.argv:
            idx = sys.argv.index('--interval')
            if idx + 1 < len(sys.argv):
                watch_interval = int(sys.argv[idx + 1])
        return cmd_watch(once=once, interval=watch_interval,
                         install_cron=install_cron, install_launchd=install_launchd)
    elif command == 'alerts':
        return cmd_alerts()
    elif command == 'remix':
        target = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
        role = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
        return cmd_remix(target, role=role)
    elif command == 'list':
        return cmd_list(limit=limit, days=days)
    elif command == 'serve':
        host = '127.0.0.1'
        port = 8000
        if '--host' in sys.argv:
            idx = sys.argv.index('--host')
            if idx + 1 < len(sys.argv):
                host = sys.argv[idx + 1]
        if '--port' in sys.argv:
            idx = sys.argv.index('--port')
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
        return cmd_serve(host=host, port=port)
    elif command == 'config':
        return cmd_config_check()
    elif command == 'export':
        return cmd_export()
    else:
        print(f'✗ Unknown command: {command}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
