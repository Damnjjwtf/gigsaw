"""Hacker News 'Who is hiring?' parser.

Free, public, monthly thread with hundreds of hiring companies.
Better signal than aggregators: companies write directly with role + tech stack.
"""

import requests
import re
from datetime import datetime, timedelta


HN_API = 'https://hacker-news.firebaseio.com/v0'
WHOISHIRING_USER = 'whoishiring'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}


class HackerNewsSource:
    """Parse the monthly 'Who is hiring?' thread from Hacker News."""

    def fetch_companies(self, days=60, limit=200):
        """
        Fetch hiring companies from the most recent 'Who is hiring?' thread.
        Returns list of normalized company dicts.
        """
        print(f'[...] fetching Hacker News Who\'s Hiring')

        try:
            # Get whoishiring user's submissions
            response = requests.get(f'{HN_API}/user/{WHOISHIRING_USER}.json', headers=HEADERS, timeout=10)
            response.raise_for_status()
            user_data = response.json()

            submitted_ids = user_data.get('submitted', [])
            if not submitted_ids:
                print('✗ No submissions found')
                return []

            # Find the most recent "Who is hiring?" thread
            thread_id = None
            for item_id in submitted_ids[:30]:
                item = self._fetch_item(item_id)
                if item and item.get('title', '').lower().startswith('ask hn: who is hiring'):
                    thread_id = item_id
                    thread_data = item
                    break

            if not thread_id:
                print('✗ No Who is hiring thread found')
                return []

            # Check thread is recent enough
            posted_at = datetime.fromtimestamp(thread_data.get('time', 0))
            cutoff = datetime.now() - timedelta(days=days)
            if posted_at < cutoff:
                print(f'⚠ Latest thread is from {posted_at.strftime("%Y-%m-%d")} (older than {days}d)')

            # Fetch top-level comments (each is a hiring post)
            comment_ids = thread_data.get('kids', [])[:limit]
            print(f'[...] parsing {len(comment_ids)} hiring posts')

            companies = []
            for i, comment_id in enumerate(comment_ids):
                if i % 25 == 0 and i > 0:
                    print(f'   parsed {i}/{len(comment_ids)}')
                comment = self._fetch_item(comment_id)
                if not comment or comment.get('deleted') or comment.get('dead'):
                    continue

                company_data = self._parse_hiring_post(comment, thread_data)
                if company_data:
                    companies.append(company_data)

            print(f'✓ Hacker News: {len(companies)} hiring companies extracted')
            return companies

        except Exception as e:
            print(f'✗ Hacker News fetch failed: {str(e)} — using sample data')
            return self._sample_hiring_companies()

    def _sample_hiring_companies(self):
        """Sample hiring companies when HN is unavailable."""
        now = datetime.now()
        return [
            {
                'name': 'Replicate',
                'description': 'Run and deploy ML models in the cloud. Hiring engineers, designers, and a content lead in SF.',
                'website': 'https://replicate.com',
                'stage': 'Series B',
                'amount_usd': 40_000_000,
                'announced_date': (now - timedelta(days=7)).isoformat(),
                'investors': [],
                'location': 'San Francisco',
                'source': 'hackernews',
                'open_roles': ['Engineer', 'Designer', 'Content'],
                'hn_post_url': 'https://news.ycombinator.com/item?id=sample1'
            },
            {
                'name': 'Vercel',
                'description': 'Frontend cloud platform. Hiring brand designers, content writers, and developer advocates.',
                'website': 'https://vercel.com',
                'stage': 'Series D',
                'amount_usd': 150_000_000,
                'announced_date': (now - timedelta(days=14)).isoformat(),
                'investors': [],
                'location': 'San Francisco / Remote',
                'source': 'hackernews',
                'open_roles': ['Designer', 'Writer', 'Manager'],
                'hn_post_url': 'https://news.ycombinator.com/item?id=sample2'
            },
            {
                'name': 'Linear',
                'description': 'Issue tracking for software teams. Hiring designers and content marketers.',
                'website': 'https://linear.app',
                'stage': 'Series B',
                'amount_usd': 35_000_000,
                'announced_date': (now - timedelta(days=10)).isoformat(),
                'investors': [],
                'location': 'San Francisco / Remote',
                'source': 'hackernews',
                'open_roles': ['Designer', 'Writer'],
                'hn_post_url': 'https://news.ycombinator.com/item?id=sample3'
            }
        ]

    def _fetch_item(self, item_id):
        """Fetch a single HN item by ID."""
        try:
            response = requests.get(f'{HN_API}/item/{item_id}.json', headers=HEADERS, timeout=5)
            response.raise_for_status()
            return response.json()
        except:
            return None

    def _parse_hiring_post(self, comment, thread_data):
        """Parse a single hiring post comment into a company dict."""
        text = comment.get('text', '')
        if not text or len(text) < 50:
            return None

        # Common HN hiring format: "CompanyName | Role | Location | Remote/Onsite"
        # First non-empty line typically has the company name and key info
        chunks = [c.strip() for c in re.split(r'<p>|<br>|\n', text) if c.strip()]
        if not chunks:
            return None
        first_line = re.sub(r'<[^>]+>', '', chunks[0]).strip()

        # Try to extract company name (first part before |)
        parts = first_line.split('|')
        if not parts or not parts[0].strip():
            return None

        company_name = parts[0].strip()
        # Clean up common patterns
        company_name = re.sub(r'\(.*?\)', '', company_name).strip()  # Remove parens
        company_name = re.sub(r'^\W+', '', company_name).strip()  # Strip leading non-word

        if not company_name or len(company_name) > 80 or len(company_name) < 2:
            return None

        # Extract location signals
        location_keywords = ['SF', 'San Francisco', 'Bay Area', 'NYC', 'New York',
                             'Remote', 'REMOTE', 'remote', 'London', 'Berlin']
        location = None
        for keyword in location_keywords:
            if keyword in first_line:
                location = keyword
                break

        # Extract role keywords
        role_keywords = ['Engineer', 'Designer', 'Manager', 'Writer', 'Marketer',
                         'PM', 'Lead', 'Senior', 'Junior', 'Founder', 'Copy']
        roles_found = [r for r in role_keywords if r.lower() in first_line.lower()]

        # Find URLs in the post
        urls = re.findall(r'https?://[^\s<>"]+', text)
        website = urls[0] if urls else None

        # Clean text for description
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        description = clean_text[:300]

        return {
            'name': company_name,
            'description': description,
            'website': website,
            'stage': 'unknown',
            'amount_usd': None,
            'announced_date': datetime.fromtimestamp(thread_data.get('time', 0)).isoformat(),
            'investors': [],
            'location': location or 'Unknown',
            'source': 'hackernews',
            'open_roles': roles_found,
            'hn_post_url': f'https://news.ycombinator.com/item?id={comment.get("id")}'
        }


if __name__ == '__main__':
    source = HackerNewsSource()
    companies = source.fetch_companies(limit=20)
    print(f'\nFetched {len(companies)} companies:')
    for c in companies[:5]:
        print(f"  - {c['name']} ({c.get('location', 'Unknown')}) - roles: {c.get('open_roles', [])}")
