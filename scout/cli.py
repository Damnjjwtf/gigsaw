#!/usr/bin/env python3

import sys
import json
from datetime import datetime
from scout.config import Config
from scout.feed import Feed
from scout.storage import ScoutStorage


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


def cmd_feed(days=60, limit=5, stage=None):
    """Fetch and display recently funded startups."""
    print(f'\n--- SCOUT FEED ---')

    # Validate config first
    if not Config.check():
        return 1

    # Fetch from enabled sources
    feed = Feed()
    companies = feed.fetch_all(days=days, sources=['techcrunch'])

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
        stage = company.get('stage', 'unknown')
        amount = format_amount(company.get('amount_usd', 0))
        date_str = format_date(company.get('announced_date', ''))

        print(f'{company_name:30} [{stage:10}] {amount:12} {date_str:12}')
        if company.get('description'):
            desc = company['description'][:80].replace('\n', ' ')
            print(f'  {desc}')
        print()

    print(f'---\n')
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
        print('\nCommands:')
        print('  feed           Fetch recent startups (TechCrunch)')
        print('  list           List companies in database')
        print('  config         Check configuration status')
        print('  export         Export companies to JSON')
        print('\nOptions:')
        print('  --days N       Set recency window (default: 60)')
        print('  --limit N      Limit results (default: 5)')
        print('  --stage SEED   Filter by funding stage')
        return 0

    command = sys.argv[1]

    # Parse options
    days = 60
    limit = 5
    stage = None
    for i, arg in enumerate(sys.argv[2:]):
        if arg == '--days' and i + 3 < len(sys.argv):
            days = int(sys.argv[i + 3])
        elif arg == '--limit' and i + 3 < len(sys.argv):
            limit = int(sys.argv[i + 3])
        elif arg == '--stage' and i + 3 < len(sys.argv):
            stage = sys.argv[i + 3]

    # Route commands
    if command == 'feed':
        return cmd_feed(days=days, limit=limit, stage=stage)
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
