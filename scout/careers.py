"""Inspect company career pages for open roles and hiring signals."""

import requests
import json
from scout.storage import ScoutStorage
from scout.config import Config


class CareerPageInspector:
    """Check company career pages for hiring activity."""

    APIFY_ACTOR_ID = 'apify/web-scraper'  # General web scraper for career pages
    APIFY_BASE_URL = 'https://api.apify.com/v2'

    def __init__(self):
        self.storage = ScoutStorage()
        self.apify_token = Config.APIFY_API_TOKEN

    def inspect_company(self, company_data):
        """
        Inspect a company's career page for open roles and hiring signals.
        Returns (open_roles, team_size, hiring_team, hiring_urgency).
        """
        company_name = company_data.get('name', '')
        website = company_data.get('website', '')

        if not website:
            return {
                'open_roles': [],
                'team_size': None,
                'hiring_team': None,
                'hiring_urgency': 'unknown'
            }

        # Try common career page URLs
        career_urls = [
            f"{website}/careers",
            f"{website}/jobs",
            f"{website}/careers/",
            f"{website}/jobs/",
            f"{website}/apply",
            f"{website}/hiring",
        ]

        print(f'[...] inspecting career page for {company_name}', end='', flush=True)

        for career_url in career_urls:
            result = self._scrape_career_page(career_url, company_name)
            if result.get('open_roles'):
                self.storage.save_inspection(
                    company_name,
                    result.get('open_roles', []),
                    result.get('team_size'),
                    result.get('hiring_team'),
                    result.get('hiring_urgency', 'unknown')
                )
                print(f' ✓ Found {len(result["open_roles"])} roles')
                return result

        print(f' ○ No career page found')
        return {
            'open_roles': [],
            'team_size': None,
            'hiring_team': None,
            'hiring_urgency': 'unknown'
        }

    def _scrape_career_page(self, url, company_name):
        """Scrape a single career page using Apify."""
        if not self.apify_token:
            return self._extract_roles_from_html(url, company_name)

        try:
            # For MVP, use requests to fetch and parse
            # Full Apify integration would use the API
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return {'open_roles': [], 'team_size': None, 'hiring_team': None, 'hiring_urgency': 'unknown'}

            html = response.text

            # Simple heuristics to detect roles (fallback)
            open_roles = self._detect_roles_in_html(html)

            if open_roles:
                return {
                    'open_roles': open_roles,
                    'team_size': None,
                    'hiring_team': None,
                    'hiring_urgency': 'high' if len(open_roles) > 3 else 'moderate'
                }

            return {'open_roles': [], 'team_size': None, 'hiring_team': None, 'hiring_urgency': 'unknown'}

        except Exception as e:
            return {'open_roles': [], 'team_size': None, 'hiring_team': None, 'hiring_urgency': 'unknown'}

    def _detect_roles_in_html(self, html):
        """Detect job roles in HTML using simple pattern matching."""
        roles = []
        keywords = [
            'engineer', 'designer', 'product manager', 'sales', 'marketing',
            'content', 'writer', 'brand', 'operations', 'finance', 'support',
            'founder', 'cto', 'ceo', 'vp', 'lead', 'senior'
        ]

        html_lower = html.lower()

        # Check for presence of job-related keywords
        found_keywords = set()
        for keyword in keywords:
            if keyword in html_lower:
                found_keywords.add(keyword)

        # If we found job-related content, assume they're hiring
        if found_keywords:
            roles = list(found_keywords)[:5]  # Top 5 detected roles

        return roles

    def format_inspection_report(self, company_name, inspection):
        """Format inspection results for display."""
        open_roles = inspection.get('open_roles', [])
        hiring_urgency = inspection.get('hiring_urgency', 'unknown')

        if not open_roles:
            return f"\n{company_name}: No open career page found\n"

        roles_str = ', '.join(open_roles) if open_roles else 'Unknown'
        return f"""
{company_name}:
  Hiring Urgency: {hiring_urgency}
  Detected Roles: {roles_str}
"""
