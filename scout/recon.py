"""Deep company research via Claude.

Synthesizes everything we know about a target company into a recon brief
that feeds /scout build, /scout propose, and /scout arbitrage.
"""

from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from scout.config import Config
from scout.storage import ScoutStorage


RECON_SYSTEM_PROMPT = """You are the Recon Engine for JJ's job search system.

Your job: take what we know about a target company (from SCOUT data) and synthesize it into a recon brief that supports decisions about whether to build for them, propose a role, or run a wild play.

JJ's positioning:
- Copywriter & Creative Intelligence Engineer (CIE)
- Shipped: ZETTA Trials, Cribsheet, The Recipe Book
- Building: Jeli, HydePark.news, fandom.market

The brief should help JJ answer: should I invest a weekend building for this company? What angle? What's the gap?

Be honest. If the company is a weak fit despite hype, say so. If you don't have enough data to judge a dimension, say "insufficient data."

Output format (Markdown):

# Recon: [Company Name]

## Snapshot
[2-3 sentences. What they do, who they sell to, where they are in the market.]

## Why They Matter to JJ
[2-3 sentences on the specific angle for JJ. NOT generic — tie to his shipped work or CIE positioning.]

## Public-Facing Gaps
[3-5 bullet points on observable gaps in their product, content, brand, or community. These are build/proposal opportunities.]

## Hiring Pattern
[1-2 sentences on what their open roles + recent posts suggest about team structure and hiring direction.]

## AI Posture
[1-2 sentences on whether they mention AI in product/job posts, and where they sit on the AI-adoption curve.]

## The Build Angle
[1-2 sentences: if JJ were to ship something for this company, what's the strongest angle? Be specific.]

## The Proposal Angle
[1-2 sentences: is there a role they're splitting across hires that JJ could propose? Or is the posted role the right target?]

## The Wild Play
[1 sentence: what's the unorthodox angle if standard outreach fails?]

## Verdict
**Recommended Action:** [Build / Propose / Apply / Skip / Watch]
**Reasoning:** [1-2 sentences. Honest.]

Keep under 600 words."""


class ReconEngine:
    """Deep company research using SCOUT data + Claude synthesis."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()
        self.output_dir = Path(__file__).parent.parent / 'data' / 'recon'

    def deep_dive(self, company_name):
        """
        Generate a deep recon brief for a company.

        Pulls everything we know from storage + scores + drafts + inspections,
        feeds to Claude for synthesis.
        """
        company = self.storage.get_company(company_name)
        if not company:
            return {
                'report': f'Company "{company_name}" not found in database. Run /scout feed first.',
                'company': company_name,
                'success': False
            }

        # Gather all available signals
        score_data = self._get_latest_score(company_name)
        inspection = self.storage.get_inspection(company_name)
        draft = self.storage.get_draft(company_name)

        # Build context
        context = f"""TARGET: {company_name}

BASIC DATA:
- Stage: {company.get('stage', 'unknown')}
- Funding: ${company.get('amount_usd', 0):,}
- Announced: {company.get('announced_date', 'unknown')}
- Description: {company.get('description', '')}
- Investors: {', '.join(company.get('investors', []) or [])}
- Website: {company.get('website', 'unknown')}
- Location: {company.get('location', 'unknown')}
- Source: {company.get('source', 'unknown')}
"""

        if score_data:
            context += f"""
SCOUT SCORE:
- Score: {score_data.get('score', 'N/A')}/100
- Rationale: {score_data.get('rationale', 'N/A')}
"""

        if inspection:
            context += f"""
CAREER PAGE INSPECTION:
- Open Roles: {', '.join(inspection.get('open_roles', []) or [])}
- Hiring Urgency: {inspection.get('hiring_urgency', 'unknown')}
"""

        if draft:
            context += f"""
PRIOR OUTREACH DRAFT:
- Subject: {draft.get('subject', 'N/A')}
"""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1800,
                system=RECON_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}]
            )

            report = response.content[0].text.strip()
            output_path = self._save_report(report, company_name)

            return {
                'report': report,
                'company': company_name,
                'saved_to': str(output_path),
                'success': True
            }

        except Exception as e:
            return {
                'report': f'[Recon generation failed: {str(e)}]',
                'company': company_name,
                'success': False
            }

    def _get_latest_score(self, company_name):
        """Get the most recent score for a company."""
        import sqlite3
        try:
            with sqlite3.connect(Config.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute('''
                    SELECT * FROM scores WHERE company_name = ?
                    ORDER BY timestamp DESC LIMIT 1
                ''', (company_name,)).fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def _save_report(self, report, company_name):
        """Save recon report to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        slug = company_name.lower().replace(' ', '_').replace('/', '_')
        output_path = self.output_dir / f'{slug}.md'

        with open(output_path, 'w') as f:
            f.write(report)
            f.write(f'\n\n---\n_Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}_\n')

        return output_path
