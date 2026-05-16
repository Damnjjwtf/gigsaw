"""Pipeline dashboard — at-a-glance view of SCOUT state."""

import sqlite3
from datetime import datetime, timedelta
from scout.config import Config
from scout.storage import ScoutStorage


class Dashboard:
    """Render a terminal dashboard of pipeline state."""

    def __init__(self):
        self.storage = ScoutStorage()

    def render(self):
        """Render the full dashboard."""
        stats = self._gather_stats()

        output = []
        output.append('')
        output.append('=' * 60)
        output.append('SCOUT DASHBOARD'.center(60))
        output.append(datetime.now().strftime('%Y-%m-%d %H:%M').center(60))
        output.append('=' * 60)
        output.append('')

        # Pipeline stats
        output.append('PIPELINE')
        output.append('-' * 60)
        output.append(f'  Total companies in database:  {stats["total_companies"]}')
        output.append(f'  Added in last 7 days:         {stats["recent_companies"]}')
        output.append(f'  Scored:                        {stats["scored"]}')
        output.append(f'  With outreach drafts:          {stats["drafted"]}')
        output.append(f'  Career pages inspected:        {stats["inspected"]}')
        output.append(f'  Pushed to GIGSAW:              {stats["pushed_gigsaw"]}')
        output.append('')

        # Score distribution
        output.append('SCORE DISTRIBUTION')
        output.append('-' * 60)
        for bucket, count in stats['score_buckets'].items():
            bar = '█' * min(count, 30)
            output.append(f'  {bucket:10s} {bar} {count}')
        output.append('')

        # Top targets
        if stats['top_targets']:
            output.append('TOP TARGETS (score >= 80)')
            output.append('-' * 60)
            for company in stats['top_targets']:
                name = company['name'][:30].ljust(30)
                score = company.get('score', 'N/A')
                stage = (company.get('stage', '') or '')[:12]
                output.append(f'  {name} {score:>3}  {stage}')
            output.append('')
        else:
            output.append('TOP TARGETS')
            output.append('-' * 60)
            output.append('  No targets scored 80+ yet. Run /scout score.')
            output.append('')

        # Recent runs
        if stats['recent_runs']:
            output.append('RECENT FETCHES')
            output.append('-' * 60)
            for run in stats['recent_runs']:
                ts = run['timestamp'][:16].replace('T', ' ')
                source = run['source'].ljust(15)
                found = run['companies_found']
                new = run['companies_new']
                output.append(f'  {ts}  {source}  {found:3} found, {new:3} new')
            output.append('')

        # Suggested actions
        output.append('SUGGESTED NEXT ACTIONS')
        output.append('-' * 60)
        actions = self._suggest_actions(stats)
        for action in actions:
            output.append(f'  → {action}')
        output.append('')

        output.append('=' * 60)
        return '\n'.join(output)

    def _gather_stats(self):
        """Gather all stats from the database."""
        with sqlite3.connect(Config.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            total = conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0]

            recent = conn.execute('''
                SELECT COUNT(*) FROM companies
                WHERE datetime(last_fetched) >= datetime('now', '-7 days')
            ''').fetchone()[0]

            scored = conn.execute('SELECT COUNT(DISTINCT company_name) FROM scores').fetchone()[0]
            drafted = conn.execute('SELECT COUNT(DISTINCT company_name) FROM drafts').fetchone()[0]
            inspected = conn.execute('SELECT COUNT(DISTINCT company_name) FROM inspections').fetchone()[0]

            # Score buckets
            buckets = {
                'A (90-100)': 0,
                'B (80-89)':  0,
                'C (70-79)':  0,
                'D (60-69)':  0,
                'F (0-59)':   0,
            }
            scores = conn.execute('''
                SELECT company_name, MAX(score) as max_score
                FROM scores GROUP BY company_name
            ''').fetchall()
            for row in scores:
                s = row['max_score']
                if s >= 90: buckets['A (90-100)'] += 1
                elif s >= 80: buckets['B (80-89)'] += 1
                elif s >= 70: buckets['C (70-79)'] += 1
                elif s >= 60: buckets['D (60-69)'] += 1
                else: buckets['F (0-59)'] += 1

            # Top targets
            top_targets_rows = conn.execute('''
                SELECT c.name, c.stage, MAX(s.score) as score
                FROM companies c
                JOIN scores s ON c.name = s.company_name
                GROUP BY c.name
                HAVING MAX(s.score) >= 80
                ORDER BY score DESC LIMIT 10
            ''').fetchall()
            top_targets = [dict(r) for r in top_targets_rows]

            # Recent runs
            recent_runs_rows = conn.execute('''
                SELECT timestamp, source, companies_found, companies_new
                FROM runs ORDER BY timestamp DESC LIMIT 5
            ''').fetchall()
            recent_runs = [dict(r) for r in recent_runs_rows]

            # Pushed to GIGSAW (count tracker entries)
            pushed_gigsaw = self._count_gigsaw_pushed()

        return {
            'total_companies': total,
            'recent_companies': recent,
            'scored': scored,
            'drafted': drafted,
            'inspected': inspected,
            'pushed_gigsaw': pushed_gigsaw,
            'score_buckets': buckets,
            'top_targets': top_targets,
            'recent_runs': recent_runs
        }

    def _count_gigsaw_pushed(self):
        """Count entries in GIGSAW applications tracker."""
        from pathlib import Path
        tracker = Path('/home/user/gigsaw/data/applications.tsv')
        if not tracker.exists():
            return 0
        try:
            with open(tracker) as f:
                # Subtract 1 for header
                return max(0, sum(1 for _ in f) - 1)
        except Exception:
            return 0

    def _suggest_actions(self, stats):
        """Suggest next actions based on pipeline state."""
        actions = []

        if stats['total_companies'] == 0:
            actions.append('Run /scout feed to fetch initial startups')
            return actions

        unscored = stats['total_companies'] - stats['scored']
        if unscored > 0:
            actions.append(f'Run /scout score — {unscored} companies are unscored')

        if stats['top_targets']:
            for target in stats['top_targets'][:3]:
                name = target['name']
                actions.append(f'Run /scout draft "{name}" — score {target["score"]}')
                if len(actions) >= 5:
                    break

        if stats['recent_companies'] == 0:
            actions.append('Run /scout feed — no fresh data in the last 7 days')

        if not actions:
            actions.append('Pipeline is current. Run /scout wild for unorthodox plays.')

        return actions
