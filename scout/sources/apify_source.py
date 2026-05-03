"""Apify-based scrapers for Y Combinator and Sequoia Capital portfolios.

Uses the Apify API to run web scraping actors. Requires APIFY_API_TOKEN.
Falls back gracefully when API is unavailable.
"""

import requests
import time
from datetime import datetime, timedelta
from scout.config import Config


APIFY_BASE = 'https://api.apify.com/v2'


class ApifyScraper:
    """Scrape startup data using Apify actors."""

    def __init__(self):
        self.token = Config.APIFY_API_TOKEN

    def fetch_yc_companies(self, batch_filter='active', limit=50):
        """
        Fetch Y Combinator companies via Apify scraper.
        Uses the public web-scraper actor with YC's public companies page.
        """
        if not self.token:
            print('⚠ APIFY_API_TOKEN not set — using sample YC data')
            return self._sample_yc_data()

        print(f'[...] fetching Y Combinator via Apify (limit: {limit})')

        try:
            # Use Apify's web-scraper actor for YC
            # https://www.ycombinator.com/companies?status=Active
            actor_input = {
                'startUrls': [{'url': 'https://www.ycombinator.com/companies?status=Active'}],
                'pageFunction': '''async function pageFunction(context) {
                    const { request, log, jQuery: $ } = context;
                    const companies = [];
                    $('a._company_86jzd_338').each((i, el) => {
                        const $el = $(el);
                        companies.push({
                            name: $el.find('._coName_86jzd_453').text().trim(),
                            description: $el.find('._coDescription_86jzd_478').text().trim(),
                            location: $el.find('._coLocation_86jzd_490').text().trim(),
                            url: 'https://www.ycombinator.com' + $el.attr('href')
                        });
                    });
                    return companies;
                }''',
                'maxRequestsPerCrawl': 1,
                'maxResultsPerCrawl': limit
            }

            return self._run_actor('apify/web-scraper', actor_input, source='yc', limit=limit)

        except Exception as e:
            print(f'✗ Apify YC fetch failed: {str(e)} — using sample data')
            return self._sample_yc_data()

    def fetch_sequoia_companies(self, limit=50):
        """Fetch Sequoia Capital portfolio via Apify."""
        if not self.token:
            print('⚠ APIFY_API_TOKEN not set — using sample Sequoia data')
            return self._sample_sequoia_data()

        print(f'[...] fetching Sequoia via Apify (limit: {limit})')

        try:
            actor_input = {
                'startUrls': [{'url': 'https://www.sequoiacap.com/our-companies/'}],
                'pageFunction': '''async function pageFunction(context) {
                    const { request, log, jQuery: $ } = context;
                    const companies = [];
                    $('.companies-grid .company-card').each((i, el) => {
                        const $el = $(el);
                        companies.push({
                            name: $el.find('.company-name').text().trim(),
                            description: $el.find('.company-description').text().trim(),
                            url: $el.find('a').attr('href')
                        });
                    });
                    return companies;
                }''',
                'maxRequestsPerCrawl': 1,
                'maxResultsPerCrawl': limit
            }

            return self._run_actor('apify/web-scraper', actor_input, source='sequoia', limit=limit)

        except Exception as e:
            print(f'✗ Apify Sequoia fetch failed: {str(e)} — using sample data')
            return self._sample_sequoia_data()

    def _run_actor(self, actor_id, input_data, source='unknown', timeout=90, limit=50):
        """Run an Apify actor and wait for results."""
        actor_id_safe = actor_id.replace('/', '~')

        # Start the run
        run_url = f'{APIFY_BASE}/acts/{actor_id_safe}/runs?token={self.token}'
        response = requests.post(run_url, json=input_data, timeout=15)
        response.raise_for_status()
        run_data = response.json()
        run_id = run_data.get('data', {}).get('id')

        if not run_id:
            print('✗ Failed to start Apify run')
            return []

        # Poll for completion
        status_url = f'{APIFY_BASE}/actor-runs/{run_id}?token={self.token}'
        elapsed = 0
        poll_interval = 3

        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval

            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json().get('data', {})
            status = status_data.get('status')

            if status == 'SUCCEEDED':
                # Fetch the dataset
                dataset_id = status_data.get('defaultDatasetId')
                items_url = f'{APIFY_BASE}/datasets/{dataset_id}/items?token={self.token}&limit={limit}'
                items_response = requests.get(items_url, timeout=15)
                raw_items = items_response.json()

                # Normalize to scout format
                companies = []
                now = datetime.now().isoformat()
                for item in raw_items[:limit]:
                    if not item.get('name'):
                        continue
                    companies.append({
                        'name': item.get('name'),
                        'description': item.get('description', '')[:300],
                        'website': item.get('url', ''),
                        'stage': 'unknown',
                        'amount_usd': None,
                        'announced_date': now,
                        'investors': [source.title()],
                        'location': item.get('location', 'Unknown'),
                        'source': source
                    })

                print(f'✓ {source}: {len(companies)} companies extracted via Apify')
                return companies

            elif status in ('FAILED', 'ABORTED', 'TIMED-OUT'):
                print(f'✗ Apify run {status}')
                return []

            print(f'   waiting... ({elapsed}s, status: {status})', end='\r', flush=True)

        print(f'✗ Apify timeout after {timeout}s')
        return []

    def _sample_yc_data(self):
        """Sample YC companies when Apify unavailable."""
        now = datetime.now()
        return [
            {
                'name': 'Pinecone',
                'description': 'Vector database for AI applications',
                'website': 'https://pinecone.io',
                'stage': 'Series B',
                'amount_usd': 100_000_000,
                'announced_date': (now - timedelta(days=20)).isoformat(),
                'investors': ['Sequoia', 'Menlo Ventures'],
                'location': 'San Francisco, CA',
                'source': 'yc'
            },
            {
                'name': 'Retool',
                'description': 'Internal tool builder for enterprises',
                'website': 'https://retool.com',
                'stage': 'Series B',
                'amount_usd': 40_000_000,
                'announced_date': (now - timedelta(days=35)).isoformat(),
                'investors': ['Spark Capital', 'Khosla'],
                'location': 'San Francisco, CA',
                'source': 'yc'
            }
        ]

    def _sample_sequoia_data(self):
        """Sample Sequoia companies when Apify unavailable."""
        now = datetime.now()
        return [
            {
                'name': 'OpenAI',
                'description': 'AI research and deployment company',
                'website': 'https://openai.com',
                'stage': 'Series E+',
                'amount_usd': 200_000_000,
                'announced_date': (now - timedelta(days=12)).isoformat(),
                'investors': ['Sequoia', 'Microsoft'],
                'location': 'San Francisco, CA',
                'source': 'sequoia'
            }
        ]
