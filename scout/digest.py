"""Daily digest generator — synthesizes new high-value targets into an actionable summary."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from anthropic import Anthropic
from scout.config import Config
from scout.storage import ScoutStorage


DIGEST_SYSTEM_PROMPT = """You are JJ's daily intelligence briefing.

Your job: take a raw list of newly-scored startups and write a tight, scannable digest that surfaces what matters and what JJ should do TODAY.

Output format (Markdown):

# SCOUT DIGEST — [date]

## Top Move Today
[1-2 sentences. The single most important action. Specific company, specific play.]

## High-Value Targets
For each company scoring 80+ (max 5):
- **[Company Name]** — Score [X]/100. [One-line: why it matters + the angle.]

## On the Watch List
For each company scoring 70-79 (max 3):
- **[Company Name]** — [Why it's worth tracking, not yet acting on.]

## Pattern Notice
[One paragraph: what the day's data reveals. A hiring wave? A funding cluster? Don't force it — only call out a real pattern.]

## Action Queue
- [ ] [specific action 1]
- [ ] [specific action 2]
- [ ] [specific action 3]

Keep it under 400 words. No filler. JJ skims this in 60 seconds before coffee."""


class DigestGenerator:
    """Generate daily intelligence digests using Claude."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()

    def generate(self, days=1):
        """
        Generate a digest for companies scored in the last N days.
        Returns the digest as markdown string.
        """
        # Gather raw data
        targets = self._gather_recent_scores(days=days)

        if not targets:
            return self._empty_digest()

        # Build context for Claude
        target_summary = '\n'.join([
            f"- {t['name']} | Score: {t['score']} | Stage: {t.get('stage', '?')} | "
            f"Funding: ${t.get('amount_usd', 0):,} | Source: {t.get('source', '?')} | "
            f"Description: {t.get('description', '')[:150]}"
            for t in targets[:30]
        ])

        date_str = datetime.now().strftime('%A, %B %d, %Y')

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1500,
                system=DIGEST_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"""Date: {date_str}

Raw target data ({len(targets)} companies scored in last {days}d):

{target_summary}

Synthesize the digest. Be specific. Name names. Suggest concrete actions."""
                }]
            )

            digest_md = response.content[0].text.strip()
            self._save_digest(digest_md)
            return digest_md

        except Exception as e:
            return f'[Digest generation failed: {str(e)}]'

    def _gather_recent_scores(self, days=1):
        """Gather companies scored in last N days."""
        with sqlite3.connect(Config.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(f'''
                SELECT c.*, s.score, s.rationale, s.timestamp as scored_at
                FROM companies c
                JOIN scores s ON c.name = s.company_name
                WHERE datetime(s.timestamp) >= datetime('now', '-{days} days')
                ORDER BY s.score DESC
            ''').fetchall()

            return [dict(row) for row in rows]

    def _empty_digest(self):
        """Return a digest when no recent scores exist."""
        date_str = datetime.now().strftime('%A, %B %d, %Y')
        return f"""# SCOUT DIGEST — {date_str}

## Top Move Today
No new scored targets. Run `/scout feed` and `/scout score` to populate the pipeline.

## Action Queue
- [ ] Run /scout feed to fetch fresh startups
- [ ] Run /scout score to evaluate against your profile
- [ ] Re-run this digest after scoring completes
"""

    def _save_digest(self, digest_md):
        """Save digest to file."""
        digest_dir = Path(Config.EXPORT_DIR) / 'digests'
        digest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d')
        digest_file = digest_dir / f'digest_{timestamp}.md'

        with open(digest_file, 'w') as f:
            f.write(digest_md)

        return digest_file
