"""Generate cold outreach drafts using Claude API."""

from anthropic import Anthropic
from scout.storage import ScoutStorage
from scout.config import Config


OUTREACH_SYSTEM_PROMPT = """You are a cold outreach specialist writing to founders and hiring leads at startups.

Your goal: Write a short, direct, warm cold outreach message that uses the funding announcement as a hook.

The message is from JJ:
- Copywriter & Creative Intelligence Engineer (CIE)
- Recent Academy graduate from Goodby Silverstein & Partners
- Shipped: ZETTA Trials (interactive fiction), Cribsheet (real estate CMA), The Recipe Book
- Currently building: Jeli (narrative OS), HydePark.news, fandom.market

TONE: Direct, warm, no fluff. Not a cover letter. A signal.
LENGTH: 3-4 sentences maximum in the body. This is a message, not a pitch deck.
HOOK: Use the funding announcement specifically (round, amount, timing, investors).
ASK: Specific, low friction (usually: "10 min call" or "take a look at X").

Format:
TO: [Likely recipient — founder or hiring lead if identifiable]
SUBJECT: [Hook + value signal in one line]

[Body: 2-3 sentences max]

— JJ

Return ONLY the formatted message. No preamble, no explanation."""


class DraftEngine:
    """Generate cold outreach drafts using Claude API."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()

    def generate_draft(self, company_data, score_result=None):
        """
        Generate a cold outreach draft for a company.
        Returns (subject, body, tone).
        """
        try:
            # Prepare context for Claude
            prompt = f"""Generate a cold outreach message for:

COMPANY: {company_data.get('name')}
STAGE: {company_data.get('stage')}
FUNDING: ${company_data.get('amount_usd', 0):,} raised
ANNOUNCED: {company_data.get('announced_date')}
INVESTORS: {', '.join(company_data.get('investors', [])) or 'Unknown'}
DESCRIPTION: {company_data.get('description', '')}
WEBSITE: {company_data.get('website') or 'Unknown'}

{f"SCORE NOTES: {score_result.get('rationale', '')}" if score_result else ""}

Write a 3-4 sentence outreach that hooks on the funding announcement and signals what JJ brings."""

            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=300,
                system=OUTREACH_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            draft_text = response.content[0].text.strip()

            # Parse the draft to extract subject and body
            subject = ""
            body = ""

            lines = draft_text.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('SUBJECT:'):
                    subject = line.replace('SUBJECT:', '').strip()
                elif line.startswith('[') and line.endswith(']'):
                    # Likely the body in brackets
                    body = '\n'.join(lines[i:]).strip()
                elif subject and not body and not line.startswith('TO:'):
                    # Start collecting body after subject
                    body = '\n'.join(lines[i:]).strip()

            # If parsing didn't work perfectly, use the whole thing
            if not subject or not body:
                body = draft_text

            # Save draft
            self.storage.save_draft(
                company_data.get('name'),
                subject or f"Congrats on the {company_data.get('stage')} — {company_data.get('name')}",
                body,
                tone='warm'
            )

            return {
                'subject': subject or f"Congrats on the {company_data.get('stage')} — {company_data.get('name')}",
                'body': body,
                'tone': 'warm'
            }

        except Exception as e:
            return {
                'subject': f"Congrats on the {company_data.get('stage')} — {company_data.get('name')}",
                'body': f'[Draft generation error: {str(e)}]',
                'tone': 'warm'
            }

    def format_draft(self, company_name, draft_data):
        """Format a draft for display."""
        return f"""
TO: [Hiring lead / Founder name]
SUBJECT: {draft_data.get('subject')}

{draft_data.get('body')}

— JJ
---
"""
