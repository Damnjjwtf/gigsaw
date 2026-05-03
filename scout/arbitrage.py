"""Intelligence Arbitrage Engine.

The core differentiator: read job descriptions as lagging indicators.
Identify what the role is BECOMING as AI capabilities reshape it.
Position JJ in the gap between the job as written and the job as it's becoming.
"""

import json
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from scout.config import Config
from scout.storage import ScoutStorage


ARBITRAGE_SYSTEM_PROMPT = """You are the Intelligence Arbitrage Engine — the core differentiator of JJ's job search system.

Your job: read a job description as a LAGGING INDICATOR. Identify what the role is BECOMING in the next 12-18 months as AI capabilities reshape it. Position JJ in the gap between what the JD says and what the role will actually be.

JJ's positioning:
- Copywriter & Creative Intelligence Engineer (CIE) — a category he coined
- Combines: narrative systems, AI-assisted creative work, copywriting, screenwriting, brand strategy
- Recent Academy graduate from Goodby Silverstein & Partners (San Francisco)
- Shipped: ZETTA Trials (interactive fiction), Cribsheet (real estate CMA), The Recipe Book
- Building: Jeli (narrative OS), HydePark.news (hyperlocal news), fandom.market (belief pricing)

CRITICAL CONSTRAINTS:
1. Be SPECIFIC about which AI capabilities reshape the role. Cite specific tools, workflows, capability shifts. Not vague "AI will change everything" platitudes.
2. Don't overstate transformation. Some roles won't change much in 12-18 months. Flag those honestly — say "this role is mostly stable, here's why" rather than forcing a narrative.
3. Tone: "I've been thinking about where this role is heading" — NOT "you don't understand your own job." Insightful, not arrogant.
4. The reframe should help JJ talk about the role intelligently in interviews — not as written, but as becoming.

Output format (Markdown):

## ROLE AS WRITTEN
[2-3 sentences summarizing the JD: stated responsibilities, required skills, tools mentioned, team structure signals.]

## ROLE AS BECOMING (12-18 months)
[2-3 sentences on what this role looks like as AI capabilities reshape it. Specific tools, workflows, capability shifts.]

## THE GAP
[1-2 sentences on what the company doesn't know they need yet — the part of the future role nobody is hiring for explicitly.]

## JJ'S POSITION IN THE GAP
[2-3 sentences on why JJ is already doing the future version. Reference specific shipped work (ZETTA Trials, Cribsheet, etc.) when relevant.]

## INTERVIEW REFRAME
[2-3 sentences on how JJ should talk about THIS role in an interview — the angle that signals he sees what the role is becoming.]

## PROOF BUILD SUGGESTION
[1 specific build JJ could ship in a weekend that demonstrates the future version of this role. Concrete artifact, not abstract.]

## CONFIDENCE
[High / Medium / Low — your honest read on whether this role will actually transform meaningfully in 12-18 months. Justify in one sentence.]

Keep it tight. Under 500 words total."""


class ArbitrageEngine:
    """Intelligence arbitrage analysis via Claude."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()
        self.output_dir = Path(Config.EXPORT_DIR).parent / 'arbitrage'

    def analyze(self, job_input, company_name=None):
        """
        Run arbitrage analysis on a job description or URL.

        Args:
            job_input: Job description text OR URL to fetch (if URL, must already be fetched)
            company_name: Optional company name for context

        Returns:
            dict with full arbitrage report
        """
        # Build context
        context = ""
        if company_name:
            company = self.storage.get_company(company_name)
            if company:
                context = f"""
ADDITIONAL COMPANY CONTEXT:
- Company: {company_name}
- Stage: {company.get('stage', 'unknown')}
- Funding: ${company.get('amount_usd', 0):,}
- Description: {company.get('description', '')}
"""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1500,
                system=ARBITRAGE_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"""Run arbitrage analysis on this job:

{context}

JOB DESCRIPTION:
{job_input}

Read it as a lagging indicator. Identify the gap. Position JJ."""
                }]
            )

            report = response.content[0].text.strip()

            # Save to disk
            self._save_report(report, company_name)

            return {
                'report': report,
                'company': company_name,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'report': f'[Arbitrage analysis failed: {str(e)}]',
                'company': company_name,
                'timestamp': datetime.now().isoformat()
            }

    def _save_report(self, report, company_name):
        """Save arbitrage report to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if company_name:
            slug = company_name.lower().replace(' ', '_').replace('/', '_')
        else:
            slug = datetime.now().strftime('%Y%m%d_%H%M%S')

        output_path = self.output_dir / f'{slug}.md'
        with open(output_path, 'w') as f:
            f.write(f'# Arbitrage Analysis: {company_name or "Untitled"}\n\n')
            f.write(f'_Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}_\n\n')
            f.write(report)

        return output_path
