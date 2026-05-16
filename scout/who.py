"""Network cross-reference — find warm paths into target companies.

Reads connections.csv (LinkedIn export format), greps for company matches,
generates personalized outreach via Claude when matches found.
"""

import csv
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from scout.config import Config
from scout.storage import ScoutStorage


CONNECTIONS_PATH = Path(__file__).parent.parent / 'data' / 'connections.csv'


WARM_OUTREACH_SYSTEM_PROMPT = """You are writing a warm-intro outreach for JJ — a copywriter and Creative Intelligence Engineer (CIE).

Your job: write a SHORT, SPECIFIC LinkedIn message to one of JJ's existing connections, asking if they'd be open to introducing him to someone at their company (or making a referral).

CONSTRAINTS:
1. This is a real person JJ knows. Reference how they likely know each other (shared school, shared employer, shared event).
2. NEVER fake a personal detail. If you don't know how they're connected, write generically but warmly.
3. Specific ask. Not "hey can we chat" — but "hey, I noticed [Company] is hiring [Role] / shipping [thing]; would you be open to making an intro to [specific person or 'whoever leads X']?"
4. Lead with their context, end with the ask. Don't make it about JJ for the first 2 sentences.
5. 4 sentences max. LinkedIn DM, not an email.
6. End with "happy to share what I'd bring" or similar — open the door without overpitching.

Output: just the message. No preamble. No subject line. No signature."""


class NetworkScanner:
    """Scan LinkedIn connections for warm paths into target companies."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()
        self.connections_path = CONNECTIONS_PATH

    def find_connections_at(self, company_name):
        """
        Find all connections at a target company.
        Returns list of connection dicts.
        """
        if not self.connections_path.exists():
            return {
                'connections': [],
                'error': f'connections.csv not found at {self.connections_path}',
                'hint': 'Export connections from LinkedIn → Settings → Data Privacy → Get a copy of your data → Connections'
            }

        matches = []
        company_lower = company_name.lower()

        try:
            with open(self.connections_path, encoding='utf-8') as f:
                # LinkedIn export typically has a header line + notes line
                # Common columns: First Name, Last Name, Email, Company, Position, Connected On
                content = f.read()

                # Skip the LinkedIn intro (first ~3 lines often metadata)
                # Find the actual header
                lines = content.split('\n')
                header_idx = 0
                for i, line in enumerate(lines):
                    if 'Company' in line or 'company' in line:
                        header_idx = i
                        break

                csv_text = '\n'.join(lines[header_idx:])
                reader = csv.DictReader(csv_text.splitlines())

                for row in reader:
                    # LinkedIn exports vary; check multiple common column names
                    company_field = (
                        row.get('Company', '') or
                        row.get('company', '') or
                        row.get('Current Company', '') or
                        ''
                    )

                    if company_lower in company_field.lower():
                        matches.append({
                            'first_name': row.get('First Name', '') or row.get('first_name', ''),
                            'last_name': row.get('Last Name', '') or row.get('last_name', ''),
                            'email': row.get('Email Address', '') or row.get('email', ''),
                            'company': company_field,
                            'position': row.get('Position', '') or row.get('position', '') or row.get('Title', ''),
                            'connected_on': row.get('Connected On', '') or row.get('connected_on', '')
                        })

            return {
                'connections': matches,
                'count': len(matches),
                'company': company_name
            }

        except Exception as e:
            return {
                'connections': [],
                'error': f'Failed to parse connections: {str(e)}',
                'count': 0
            }

    def generate_warm_outreach(self, connection, company_name, context=None):
        """
        Generate a personalized warm outreach to a connection.

        Args:
            connection: dict with first_name, last_name, position, company
            company_name: The company JJ wants to reach
            context: Additional context (recent funding, role of interest, etc.)
        """
        first_name = connection.get('first_name', 'there')
        position = connection.get('position', '')
        their_company = connection.get('company', '')

        prompt = f"""Write a LinkedIn message from JJ to one of his connections:

CONNECTION:
- Name: {first_name} {connection.get('last_name', '')}
- Their role: {position}
- Their company: {their_company}

JJ wants to reach: {company_name}

{f"Why now: {context}" if context else "JJ is interested in {company_name} and wants to know if {first_name} can make an intro."}

Write a 4-sentence DM asking for a warm intro. Lead with their context."""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=300,
                system=WARM_OUTREACH_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        except Exception as e:
            return f'[Warm outreach generation failed: {str(e)}]'

    def report(self, company_name, generate_drafts=False, context=None):
        """
        Generate a network report for a target company.
        Returns formatted report string.
        """
        result = self.find_connections_at(company_name)

        output = []
        output.append(f"\n--- NETWORK CHECK: {company_name} ---\n")

        if result.get('error'):
            output.append(f"⚠ {result['error']}")
            if result.get('hint'):
                output.append(f"  {result['hint']}")
            output.append('\nProceeding cold. Use /scout wild for differentiation strategies.\n')
            return '\n'.join(output)

        connections = result.get('connections', [])

        if not connections:
            output.append(f"○ No direct connections found at {company_name}")
            output.append('\nProceeding cold. Use /scout wild for differentiation strategies.\n')
            return '\n'.join(output)

        output.append(f"✓ Found {len(connections)} connection(s) at {company_name}:\n")

        for i, conn in enumerate(connections, 1):
            full_name = f"{conn['first_name']} {conn['last_name']}".strip()
            output.append(f"  {i}. {full_name}")
            if conn.get('position'):
                output.append(f"     Role: {conn['position']}")
            if conn.get('email'):
                output.append(f"     Email: {conn['email']}")
            if conn.get('connected_on'):
                output.append(f"     Connected: {conn['connected_on']}")
            output.append('')

            # Generate draft outreach if requested
            if generate_drafts:
                output.append('     SUGGESTED MESSAGE:')
                output.append('     ' + '─' * 40)
                draft = self.generate_warm_outreach(conn, company_name, context=context)
                for line in draft.split('\n'):
                    output.append(f'     {line}')
                output.append('     ' + '─' * 40 + '\n')

        return '\n'.join(output)
