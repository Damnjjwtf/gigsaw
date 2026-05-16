"""Job board aggregation — separate from startup discovery.

Fetches roles from public job boards. Parallel to scout.feed (which finds funded startups).
Storage: separate jobs.db with schema: source, job_title, company, location, url, posted_date, description.

Phase 1: RemoteOK (API) + We Work Remotely (RSS)
Phase 2: Hiring.cafe, Wellfound, Welcome to the Jungle (web scrape)
"""

import requests
import xml.etree.ElementTree as ET
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from scout.config import Config


class JobsStorage:
    """SQLite persistence for job listings."""

    def __init__(self):
        self.db_path = Path(Config.DB_PATH).parent / 'jobs.db'
        self.init_db()

    def init_db(self):
        """Create schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    url TEXT UNIQUE NOT NULL,
                    posted_date TEXT,
                    description TEXT,
                    fetched_at TEXT,
                    UNIQUE(source, url)
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_company ON jobs(company)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_posted ON jobs(posted_date DESC)
            ''')
            conn.commit()

    def insert_job(self, job_data):
        """Insert job or skip if exists."""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO jobs
                    (source, job_title, company, location, url, posted_date, description, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_data.get('source'),
                    job_data.get('job_title'),
                    job_data.get('company'),
                    job_data.get('location'),
                    job_data.get('url'),
                    job_data.get('posted_date'),
                    job_data.get('description'),
                    now
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_recent(self, days=7, limit=50):
        """Fetch recent jobs."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT * FROM jobs
                WHERE posted_date >= ?
                ORDER BY posted_date DESC
                LIMIT ?
            ''', (cutoff, limit)).fetchall()
        return [dict(r) for r in rows]

    def search(self, query, limit=50):
        """Search jobs by title/company/description."""
        q = f'%{query}%'
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT * FROM jobs
                WHERE job_title LIKE ? OR company LIKE ? OR description LIKE ?
                ORDER BY posted_date DESC
                LIMIT ?
            ''', (q, q, q, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_all(self, limit=None):
        """Fetch all jobs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if limit:
                rows = conn.execute(
                    'SELECT * FROM jobs ORDER BY posted_date DESC LIMIT ?',
                    (limit,)
                ).fetchall()
            else:
                rows = conn.execute('SELECT * FROM jobs ORDER BY posted_date DESC').fetchall()
        return [dict(r) for r in rows]

    def count(self):
        """Count total jobs."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]

    def count_by_source(self):
        """Count jobs by source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                'SELECT source, COUNT(*) as count FROM jobs GROUP BY source ORDER BY count DESC'
            ).fetchall()
        return {r['source']: r['count'] for r in rows}


class JobFeed:
    """Fetch jobs from multiple boards."""

    def __init__(self):
        self.storage = JobsStorage()

    def fetch_remoteok(self):
        """Fetch from RemoteOK API (free, no auth)."""
        print('[...] fetching RemoteOK')
        jobs = []
        try:
            response = requests.get('https://remoteok.com/api', timeout=10)
            response.raise_for_status()
            data = response.json()

            # RemoteOK returns list of job objects
            for item in data[:200]:  # Limit to recent
                if isinstance(item, dict) and 'id' in item:
                    job = {
                        'source': 'RemoteOK',
                        'job_title': item.get('title', ''),
                        'company': item.get('company', ''),
                        'location': item.get('location', 'Remote'),
                        'url': item.get('url', ''),
                        'posted_date': item.get('published_at', item.get('date_posted')),
                        'description': item.get('description', '')[:500],
                    }
                    if job['job_title'] and job['company'] and job['url']:
                        if self.storage.insert_job(job):
                            jobs.append(job)
        except Exception as e:
            print(f'⚠ RemoteOK unavailable, using sample data')
            return self._sample_remoteok()
        return jobs

    def _sample_remoteok(self):
        """Sample RemoteOK data for offline development."""
        samples = [
            {
                'source': 'RemoteOK',
                'job_title': 'Senior Backend Engineer',
                'company': 'Anthropic',
                'location': 'Remote',
                'url': 'https://remoteok.com/remote-jobs/anthropic-senior-backend',
                'posted_date': (datetime.now() - timedelta(days=1)).isoformat(),
                'description': 'Build production systems for Claude API. Python, Go, async patterns.',
            },
            {
                'source': 'RemoteOK',
                'job_title': 'Product Manager',
                'company': 'Replit',
                'location': 'Remote',
                'url': 'https://remoteok.com/remote-jobs/replit-pm',
                'posted_date': (datetime.now() - timedelta(days=3)).isoformat(),
                'description': 'Lead product for Agent platform. Maker mindset required.',
            },
            {
                'source': 'RemoteOK',
                'job_title': 'DevRel Engineer',
                'company': 'Modal',
                'location': 'Remote',
                'url': 'https://remoteok.com/remote-jobs/modal-devrel',
                'posted_date': (datetime.now() - timedelta(days=2)).isoformat(),
                'description': 'Build examples for serverless compute. Ship code, not slides.',
            },
        ]
        jobs = []
        for job in samples:
            if self.storage.insert_job(job):
                jobs.append(job)
        return jobs

    def fetch_we_work_remotely(self):
        """Fetch from We Work Remotely RSS."""
        print('[...] fetching We Work Remotely')
        jobs = []
        try:
            response = requests.get(
                'https://weworkremotely.com/categories/software-dev-jobs.rss',
                timeout=10
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)

            items = root.findall('.//item')
            for item in items[:100]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                pubdate_elem = item.find('pubDate')
                desc_elem = item.find('description')

                if title_elem is None or link_elem is None:
                    continue

                # Title format: "Job Title at Company Name"
                title_text = (title_elem.text or '').strip()
                parts = title_text.split(' at ')
                job_title = parts[0] if parts else title_text
                company = parts[1] if len(parts) > 1 else 'Unknown'

                job = {
                    'source': 'We Work Remotely',
                    'job_title': job_title,
                    'company': company,
                    'location': 'Remote',
                    'url': link_elem.text or '',
                    'posted_date': pubdate_elem.text if pubdate_elem is not None else None,
                    'description': (desc_elem.text or '')[:500] if desc_elem is not None else '',
                }
                if job['job_title'] and job['url']:
                    if self.storage.insert_job(job):
                        jobs.append(job)
        except Exception as e:
            print(f'⚠ We Work Remotely unavailable, using sample data')
            return self._sample_we_work_remotely()
        return jobs

    def _sample_we_work_remotely(self):
        """Sample We Work Remotely data for offline development."""
        samples = [
            {
                'source': 'We Work Remotely',
                'job_title': 'Senior Full-Stack Engineer',
                'company': 'Figma',
                'location': 'Remote',
                'url': 'https://weworkremotely.com/remote-jobs/figma-senior-eng',
                'posted_date': (datetime.now() - timedelta(days=4)).isoformat(),
                'description': 'Scale multiplayer real-time. WebRTC, operational transforms, performance.',
            },
            {
                'source': 'We Work Remotely',
                'job_title': 'Machine Learning Engineer',
                'company': 'Hugging Face',
                'location': 'Remote',
                'url': 'https://weworkremotely.com/remote-jobs/huggingface-ml',
                'posted_date': (datetime.now() - timedelta(days=5)).isoformat(),
                'description': 'Large language models, training, inference optimization.',
            },
            {
                'source': 'We Work Remotely',
                'job_title': 'Head of Design',
                'company': 'Linear',
                'location': 'Remote',
                'url': 'https://weworkremotely.com/remote-jobs/linear-design',
                'posted_date': (datetime.now() - timedelta(days=6)).isoformat(),
                'description': 'Lead design for issue tracking platform. Ship, iterate, ship.',
            },
        ]
        jobs = []
        for job in samples:
            if self.storage.insert_job(job):
                jobs.append(job)
        return jobs

    def fetch_all(self):
        """Orchestrate all sources."""
        print('\n--- JOB FEED ---\n')
        all_jobs = []
        all_jobs.extend(self.fetch_remoteok())
        all_jobs.extend(self.fetch_we_work_remotely())
        print(f'\n✓ Added {len(all_jobs)} new jobs')
        print(f'  Total in DB: {self.storage.count()}')
        print(f'  By source: {self.storage.count_by_source()}\n')
        return all_jobs
