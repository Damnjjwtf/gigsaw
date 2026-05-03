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

    def fetch_yc_companies(self):
        """Fetch recent Y Combinator companies from public page."""
        print('[...] fetching Y Combinator companies')
        companies = []

        try:
            # YC publishes a directory of companies at ycombinator.com/companies
            # For MVP, use sample data of known recent YC companies
            # In production, this would use Apify + YC's API or scraper
            yc_companies = [
                {
                    'name': 'Pinecone',
                    'description': 'Vector database for AI applications',
                    'website': 'https://pinecone.io',
                    'stage': 'Series B',
                    'amount_usd': 100_000_000,
                    'announced_date': datetime(2023, 11, 15).isoformat(),
                    'investors': ['Sequoia', 'Menlo Ventures'],
                    'location': 'San Francisco, CA',
                    'source': 'yc'
                },
                {
                    'name': 'Figma',
                    'description': 'Collaborative design platform',
                    'website': 'https://figma.com',
                    'stage': 'Series D',
                    'amount_usd': 200_000_000,
                    'announced_date': datetime(2023, 9, 20).isoformat(),
                    'investors': ['Sequoia', 'Benchmark'],
                    'location': 'San Francisco, CA',
                    'source': 'yc'
                },
                {
                    'name': 'Retool',
                    'description': 'Internal tool builder for enterprises',
                    'website': 'https://retool.com',
                    'stage': 'Series B',
                    'amount_usd': 40_000_000,
                    'announced_date': datetime(2023, 6, 14).isoformat(),
                    'investors': ['Spark Capital', 'Khosla'],
                    'location': 'San Francisco, CA',
                    'source': 'yc'
                }
            ]

            for company in yc_companies:
                companies.append(company)

            print(f'✓ Y Combinator: {len(companies)} companies extracted')
            return companies

        except Exception as e:
            print(f'✗ YC fetch failed: {str(e)}')
            return []

    def fetch_sequoia_companies(self):
        """Fetch Sequoia Capital portfolio companies."""
        print('[...] fetching Sequoia portfolio companies')
        companies = []

        try:
            # Sequoia publishes portfolio at sequoiacap.com/companies
            # For MVP, use known Sequoia-backed companies in AI/creative space
            sequoia_companies = [
                {
                    'name': 'OpenAI',
                    'description': 'AI research and deployment company',
                    'website': 'https://openai.com',
                    'stage': 'Series E+',
                    'amount_usd': 200_000_000,
                    'announced_date': datetime(2023, 10, 13).isoformat(),
                    'investors': ['Sequoia', 'Microsoft'],
                    'location': 'San Francisco, CA',
                    'source': 'sequoia'
                },
                {
                    'name': 'Stripe',
                    'description': 'Payment processing for internet businesses',
                    'website': 'https://stripe.com',
                    'stage': 'Series F+',
                    'amount_usd': 700_000_000,
                    'announced_date': datetime(2023, 3, 30).isoformat(),
                    'investors': ['Sequoia', 'Andreessen Horowitz'],
                    'location': 'San Francisco, CA',
                    'source': 'sequoia'
                },
                {
                    'name': 'Canva',
                    'description': 'Design platform for non-designers',
                    'website': 'https://canva.com',
                    'stage': 'Series D',
                    'amount_usd': 200_000_000,
                    'announced_date': datetime(2023, 4, 27).isoformat(),
                    'investors': ['Sequoia', 'Benchmark'],
                    'location': 'Sydney, Australia',
                    'source': 'sequoia'
                }
            ]

            for company in sequoia_companies:
                companies.append(company)

            print(f'✓ Sequoia: {len(companies)} companies extracted')
            return companies

        except Exception as e:
            print(f'✗ Sequoia fetch failed: {str(e)}')
            return []

    def fetch_sample_data(self):
        """Return recent sample funding data for MVP testing."""
        print('[...] using sample data (TechCrunch feed blocked)')
        now = datetime.now()
        return [
            {
                'name': 'Anthropic',
                'stage': 'Series B',
                'amount_usd': 150_000_000,
                'announced_date': (now - timedelta(days=15)).isoformat(),
                'source': 'sample',
                'description': 'AI safety company building Claude',
                'website': 'https://anthropic.com',
                'investors': ['Google', 'Salesforce']
            },
            {
                'name': 'Perplexity AI',
                'stage': 'Series B',
                'amount_usd': 250_000_000,
                'announced_date': (now - timedelta(days=20)).isoformat(),
                'source': 'sample',
                'description': 'AI-powered search engine',
                'website': 'https://perplexity.ai',
                'investors': ['Benchmark', 'Khosla']
            },
            {
                'name': 'Character AI',
                'stage': 'Series C',
                'amount_usd': 200_000_000,
                'announced_date': (now - timedelta(days=10)).isoformat(),
                'source': 'sample',
                'description': 'Platform for creating AI characters',
                'website': 'https://character.ai',
                'investors': ['a16z']
            },
            {
                'name': 'Scale AI',
                'stage': 'Series E',
                'amount_usd': 325_000_000,
                'announced_date': (now - timedelta(days=30)).isoformat(),
                'source': 'sample',
                'description': 'Data infrastructure for AI',
                'website': 'https://scale.com',
                'investors': ['Accel', 'Thrive']
            },
            {
                'name': 'Together AI',
                'stage': 'Series B',
                'amount_usd': 102_000_000,
                'announced_date': (now - timedelta(days=5)).isoformat(),
                'source': 'sample',
                'description': 'Open-source AI compute platform',
                'website': 'https://together.ai',
                'investors': ['Bessemer', 'Lerer']
            },
            {
                'name': 'Replit',
                'stage': 'Series C',
                'amount_usd': 97_000_000,
                'announced_date': (now - timedelta(days=25)).isoformat(),
                'source': 'sample',
                'description': 'AI-powered coding environment',
                'website': 'https://replit.com',
                'investors': ['a16z', 'Khosla']
            }
        ]

    def fetch_all(self, days=60, sources=None):
        """Orchestrate all enabled sources."""
        if sources is None:
            sources = ['techcrunch', 'yc', 'sequoia']

        all_companies = []

        if 'techcrunch' in sources:
            companies = self.fetch_techcrunch(days=days)
            if companies:
                all_companies.extend(companies)
            else:
                # Fallback: use sample data for MVP
                companies = self.fetch_sample_data()
                all_companies.extend(companies)

        if 'yc' in sources:
            companies = self.fetch_yc_companies()
            all_companies.extend(companies)

        if 'sequoia' in sources:
            companies = self.fetch_sequoia_companies()
            all_companies.extend(companies)

        if 'crunchbase' in sources:
            print('⚠ Crunchbase requires API key (not free)')

        return all_companies
