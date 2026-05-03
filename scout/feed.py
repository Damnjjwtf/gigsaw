import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from scout.storage import ScoutStorage
import re


class Feed:
    """Fetch startups from various sources."""

    TECHCRUNCH_FEED = 'https://techcrunch.com/tag/fundings-exits/feed/'

    def __init__(self):
        self.storage = ScoutStorage()

    def fetch_techcrunch(self, days=60):
        """
        Parse TechCrunch funding RSS.
        Returns list of normalized company dicts.
        """
        print(f'[...] fetching TechCrunch (last {days} days)')
        companies = []
        cutoff = datetime.now() - timedelta(days=days)

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/rss+xml, application/xml'
            }
            response = requests.get(self.TECHCRUNCH_FEED, headers=headers, timeout=10)
            response.raise_for_status()
            xml_data = response.content

            root = ET.fromstring(xml_data)

            # RSS namespace
            ns = {'': 'http://www.rss.org/2.0/', 'content': 'http://purl.org/rss/1.0/modules/content/'}

            items = root.findall('.//item')
            if not items:
                print('✗ TechCrunch feed empty or unavailable')
                return companies

            for item in items[:100]:
                try:
                    title_elem = item.find('title')
                    pubdate_elem = item.find('pubDate')
                    link_elem = item.find('link')
                    description_elem = item.find('description')

                    if title_elem is None:
                        continue

                    title = title_elem.text or ''
                    link = link_elem.text if link_elem is not None else ''

                    # Parse pub date
                    if pubdate_elem is not None and pubdate_elem.text:
                        try:
                            # RFC 2822 format: "Fri, 03 May 2024 10:30:00 +0000"
                            from email.utils import parsedate_to_datetime
                            pub_date = parsedate_to_datetime(pubdate_elem.text)
                            if pub_date.replace(tzinfo=None) < cutoff:
                                continue
                        except:
                            pub_date = datetime.now()
                    else:
                        pub_date = datetime.now()

                    # Extract company name and funding amount from title
                    # Pattern: "Company Name Raises $100M in Series A"
                    match = re.search(r'^([^a-z]*?)\s+[Rr]aises?\s+\$([\d.]+)([KMB]?)\s+(?:in\s+)?([A-Z\d\-]+)?', title)

                    if not match:
                        continue

                    company_name = match.group(1).strip()
                    if not company_name or len(company_name) > 100:
                        continue

                    amount_str = match.group(2)
                    multiplier = match.group(3) or ''
                    stage = (match.group(4) or 'unknown').strip()

                    # Normalize amount to USD
                    try:
                        amount = float(amount_str)
                        if multiplier == 'K':
                            amount *= 1000
                        elif multiplier == 'M':
                            amount *= 1_000_000
                        elif multiplier == 'B':
                            amount *= 1_000_000_000
                    except:
                        continue

                    description = ''
                    if description_elem is not None and description_elem.text:
                        description = description_elem.text[:200]

                    # Minimal company dict
                    company = {
                        'name': company_name,
                        'stage': stage,
                        'amount_usd': int(amount),
                        'announced_date': pub_date.isoformat(),
                        'source': 'techcrunch',
                        'description': description,
                        'website': '',
                        'investors': []
                    }

                    companies.append(company)
                except Exception as e:
                    continue

            print(f'✓ TechCrunch: {len(companies)} companies extracted')
            return companies

        except Exception as e:
            print(f'✗ TechCrunch fetch failed: {str(e)}')
            return []

    def save_feed(self, companies, source='techcrunch'):
        """Store companies in database. Return count of new."""
        new_count = 0
        for company in companies:
            inserted = self.storage.insert_company(company)
            if inserted:
                new_count += 1

        self.storage.log_run(source, len(companies), new_count)
        return new_count

    def fetch_sample_data(self):
        """Return recent sample funding data for MVP testing."""
        print('[...] using sample data (TechCrunch feed blocked)')
        return [
            {
                'name': 'Anthropic',
                'stage': 'Series B',
                'amount_usd': 150_000_000,
                'announced_date': datetime(2024, 1, 15).isoformat(),
                'source': 'sample',
                'description': 'AI safety company building Claude',
                'website': 'https://anthropic.com',
                'investors': ['Google', 'Salesforce']
            },
            {
                'name': 'Perplexity AI',
                'stage': 'Series B',
                'amount_usd': 250_000_000,
                'announced_date': datetime(2024, 2, 20).isoformat(),
                'source': 'sample',
                'description': 'AI-powered search engine',
                'website': 'https://perplexity.ai',
                'investors': ['Benchmark', 'Khosla']
            },
            {
                'name': 'Character AI',
                'stage': 'Series C',
                'amount_usd': 200_000_000,
                'announced_date': datetime(2024, 3, 10).isoformat(),
                'source': 'sample',
                'description': 'Platform for creating AI characters',
                'website': 'https://character.ai',
                'investors': ['a16z']
            },
            {
                'name': 'Scale AI',
                'stage': 'Series E',
                'amount_usd': 325_000_000,
                'announced_date': datetime(2024, 4, 5).isoformat(),
                'source': 'sample',
                'description': 'Data infrastructure for AI',
                'website': 'https://scale.com',
                'investors': ['Accel', 'Thrive']
            },
            {
                'name': 'Together AI',
                'stage': 'Series B',
                'amount_usd': 102_000_000,
                'announced_date': datetime(2024, 4, 25).isoformat(),
                'source': 'sample',
                'description': 'Open-source AI compute platform',
                'website': 'https://together.ai',
                'investors': ['Bessemer', 'Lerer']
            },
            {
                'name': 'Replit',
                'stage': 'Series C',
                'amount_usd': 97_000_000,
                'announced_date': datetime(2024, 2, 14).isoformat(),
                'source': 'sample',
                'description': 'AI-powered coding environment',
                'website': 'https://replit.com',
                'investors': ['a16z', 'Khosla']
            }
        ]

    def fetch_all(self, days=60, sources=['techcrunch']):
        """Orchestrate all enabled sources."""
        all_companies = []

        if 'techcrunch' in sources:
            companies = self.fetch_techcrunch(days=days)
            if companies:
                all_companies.extend(companies)
            else:
                # Fallback: use sample data for MVP
                companies = self.fetch_sample_data()
                all_companies.extend(companies)

        # TODO: Add Crunchbase, YC, Sequoia sources
        if 'crunchbase' in sources:
            print('⚠ Crunchbase not yet implemented')

        if 'yc' in sources:
            print('⚠ Y Combinator not yet implemented')

        return all_companies
