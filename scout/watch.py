"""Background watcher and scheduler for SCOUT.

Runs feed → score → digest on a schedule. Outputs cron/launchd snippets
for permanent installation. Can also run as a one-shot daemon loop.
"""

import time
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from scout.config import Config
from scout.feed import Feed
from scout.score import ScoreEngine
from scout.storage import ScoutStorage
from scout.alerts import AlertSystem


class Watcher:
    """Schedule and run periodic SCOUT pipelines."""

    LOG_FILE = Path(Config.EXPORT_DIR).parent / 'watch.log'

    def __init__(self):
        self.storage = ScoutStorage()
        self.feed = Feed()
        self.scorer = ScoreEngine() if Config.ANTHROPIC_API_KEY else None
        self.alerts = AlertSystem()

    def run_once(self, score_threshold=80, alert=True):
        """
        Run one full pipeline cycle: feed → score → alert on high-value.
        Returns summary dict.
        """
        start = datetime.now()
        self._log(f'=== Pipeline run started at {start.isoformat()} ===')

        summary = {
            'started_at': start.isoformat(),
            'fetched': 0,
            'new': 0,
            'scored': 0,
            'high_value': 0,
            'alerts_sent': 0,
            'errors': []
        }

        # Step 1: Fetch from all sources
        try:
            companies = self.feed.fetch_all()
            summary['fetched'] = len(companies)
            new_count = self.feed.save_feed(companies, source='watch_cycle')
            summary['new'] = new_count
            self._log(f'Fetched {len(companies)}, {new_count} new')
        except Exception as e:
            summary['errors'].append(f'Feed error: {e}')
            self._log(f'Feed error: {e}')

        # Step 2: Score new companies (only if scorer available)
        if self.scorer and summary['new'] > 0:
            try:
                # Score recent companies (last 7 days)
                recent = self.storage.get_recent_companies(days=7)
                # Filter to ones not yet scored — for efficiency
                unscored = [c for c in recent if not self._has_score(c['name'])]
                if unscored:
                    self._log(f'Scoring {len(unscored)} new companies')
                    results = self.scorer.score_batch(unscored, min_score=0)
                    summary['scored'] = len(results)

                    high_value = [r for r in results if r.get('score', 0) >= score_threshold]
                    summary['high_value'] = len(high_value)

                    # Step 3: Send alerts for high-value matches
                    if alert and high_value:
                        for company in high_value:
                            self.alerts.send_high_value_alert(company)
                            summary['alerts_sent'] += 1
                        self._log(f'Sent {len(high_value)} alerts')
            except Exception as e:
                summary['errors'].append(f'Scoring error: {e}')
                self._log(f'Scoring error: {e}')

        end = datetime.now()
        elapsed = (end - start).total_seconds()
        summary['ended_at'] = end.isoformat()
        summary['elapsed_seconds'] = elapsed
        self._log(f'=== Pipeline complete in {elapsed:.1f}s ===\n')

        # Save summary to disk
        self._save_summary(summary)

        return summary

    def loop(self, interval_minutes=60, max_iterations=None):
        """
        Run pipeline in a loop. Useful for foreground daemon mode.

        Args:
            interval_minutes: Wait between runs (default: 60min)
            max_iterations: Stop after N iterations (default: unlimited)
        """
        i = 0
        while True:
            i += 1
            print(f'\n[Iteration {i}] Running pipeline...')
            summary = self.run_once()
            print(f'Done. New: {summary["new"]}, Scored: {summary["scored"]}, High-value: {summary["high_value"]}')

            if max_iterations and i >= max_iterations:
                break

            print(f'Sleeping {interval_minutes}m until next run (Ctrl+C to stop)')
            try:
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print('\n[Stopping watch loop]')
                break

    def install_cron(self, frequency='hourly'):
        """
        Generate cron snippet for permanent installation.
        Returns the line to add to crontab.
        """
        python_path = sys.executable
        scout_path = Path('/home/user/gigsaw').resolve()

        schedules = {
            'hourly': '0 * * * *',
            'daily': '0 9 * * *',     # 9 AM daily
            'twice_daily': '0 9,17 * * *',  # 9 AM and 5 PM
            'weekdays': '0 9 * * 1-5',  # 9 AM Monday-Friday
        }

        schedule = schedules.get(frequency, schedules['daily'])
        env_exports = []

        if Config.ANTHROPIC_API_KEY:
            env_exports.append(f'ANTHROPIC_API_KEY="{Config.ANTHROPIC_API_KEY[:8]}..."')
        if Config.APIFY_API_TOKEN:
            env_exports.append(f'APIFY_API_TOKEN="{Config.APIFY_API_TOKEN[:8]}..."')

        env_string = ' && '.join(f'export {e}' for e in env_exports)

        cron_line = (
            f'{schedule} cd {scout_path} && '
            f'{env_string} && '
            f'{python_path} -m scout.cli watch --once >> ~/.scout/watch.log 2>&1'
        )

        return cron_line

    def install_launchd(self, frequency_seconds=3600):
        """
        Generate macOS launchd plist for permanent installation.
        Returns the plist XML string.
        """
        python_path = sys.executable
        scout_path = Path('/home/user/gigsaw').resolve()

        plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gigsaw.scout.watch</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>scout.cli</string>
        <string>watch</string>
        <string>--once</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{scout_path}</string>
    <key>StartInterval</key>
    <integer>{frequency_seconds}</integer>
    <key>StandardOutPath</key>
    <string>~/.scout/watch.log</string>
    <key>StandardErrorPath</key>
    <string>~/.scout/watch.error.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
'''
        return plist

    def _has_score(self, company_name):
        """Check if a company has been scored."""
        import sqlite3
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                row = conn.execute(
                    'SELECT 1 FROM scores WHERE company_name = ? LIMIT 1',
                    (company_name,)
                ).fetchone()
                return row is not None
        except:
            return False

    def _log(self, message):
        """Append to watch log."""
        self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.LOG_FILE, 'a') as f:
            f.write(f'[{datetime.now().isoformat()}] {message}\n')

    def _save_summary(self, summary):
        """Save run summary as JSON."""
        summaries_dir = Path(Config.EXPORT_DIR).parent / 'watch_summaries'
        summaries_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(summaries_dir / f'run_{timestamp}.json', 'w') as f:
            json.dump(summary, f, indent=2)
