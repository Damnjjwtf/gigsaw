"""Role Proposal Generator.

For companies with 'tell us about yourself' pages OR when no posted role fits.
Identifies the role split across multiple hires, proposes the missing role,
and frames it as the convergence point for JJ's CIE positioning.
"""

from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from scout.config import Config
from scout.storage import ScoutStorage


PROPOSE_SYSTEM_PROMPT = """You are the Role Proposal Generator for JJ's job search system.

Your job: when a target company doesn't have a posted role that fits, identify the role they're SPLITTING across multiple hires because they don't have the category yet — then write the role they haven't posted.

JJ's positioning:
- Copywriter & Creative Intelligence Engineer (CIE) — a category he coined
- Combines: narrative systems, AI-assisted creative work, copywriting, screenwriting, brand strategy
- Recent Academy graduate from Goodby Silverstein & Partners (San Francisco)
- Shipped: ZETTA Trials (interactive fiction), Cribsheet, The Recipe Book
- Building: Jeli, HydePark.news, fandom.market

CRITICAL CONSTRAINTS:
1. The proposal MUST demonstrate genuine insight about the company's needs — not "you should hire a CIE because CIE is cool." Show that you noticed something about THEIR specific posting pattern or product gap.
2. Keep it under 2 pages. Dense, not long.
3. Every claim about JJ should be backed by a shipped project. No hand-waving.
4. The tone is collegial — "here's what I noticed and what I'd do about it" — not "you should hire me."
5. Include at least one specific shipped project URL as proof.
6. End with a low-friction next step. Calendar link or a specific ask, not "let me know if interested."

Output format (Markdown):

# A Role You Haven't Posted Yet

**TO:** [Company]
**FROM:** JJ ([CIE]) — copywriter, creative intelligence engineer

## The Pattern I Noticed

[2-3 sentences. Specific observation about their current postings, product, or public presence. Show you did the homework.]

## The Role That's Missing

**Title:** [Specific title — make it sound real, not buzzwordy]
**Reports To:** [Likely reporting line based on the pattern]
**Function:** [One-sentence description of what this role does]

## What This Role Produces

[3-5 concrete outputs/outcomes. Not vague responsibilities. Things you'd put on a quarterly OKR.]

## Why This Role Exists Now

[1-2 sentences: the AI capability shift or product evolution that makes this role necessary RIGHT NOW.]

## Why I'm Writing This

[2-3 sentences. Brief connection to JJ's work. NOT a resume — a thesis: "I've been doing the seam between X and Y, here's what I've shipped that proves it."]

## Proof

- [Project name + URL + one-line description of what it proves]
- [Project name + URL + one-line description]
- [Project name + URL + one-line description]

## Next Step

[Specific, low-friction ask. "15-min call this week to walk through [specific topic]" — NOT "let me know if interested."]

---

Keep it under 500 words. Dense, specific, no fluff."""


class ProposeEngine:
    """Generate role proposals for companies without posted roles."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()
        self.output_dir = Path('/home/user/gigsaw/proposals')

    def generate_proposal(self, company_name, recon_notes=None, current_postings=None):
        """
        Generate a role proposal for a company.

        Args:
            company_name: Target company name
            recon_notes: Additional research notes (optional)
            current_postings: List of currently posted roles at the company (optional)
        """
        company = self.storage.get_company(company_name)

        # Build context
        context_parts = [f"Target company: {company_name}"]

        if company:
            context_parts.append(f"""
What I know:
- Stage: {company.get('stage', 'unknown')}
- Funding: ${company.get('amount_usd', 0):,}
- Description: {company.get('description', '')}
- Investors: {', '.join(company.get('investors', []) or [])}
- Website: {company.get('website', 'unknown')}""")

        if current_postings:
            context_parts.append(f"\nCurrent roles posted at this company:\n{current_postings}")

        if recon_notes:
            context_parts.append(f"\nRecon notes:\n{recon_notes}")

        user_prompt = '\n'.join(context_parts) + """

Identify the role they're splitting across multiple hires because they don't have the category yet. Write the proposal."""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1800,
                system=PROPOSE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            proposal = response.content[0].text.strip()
            output_path = self._save_proposal(proposal, company_name)

            return {
                'proposal': proposal,
                'company': company_name,
                'saved_to': str(output_path),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'proposal': f'[Proposal generation failed: {str(e)}]',
                'company': company_name,
                'timestamp': datetime.now().isoformat()
            }

    def _save_proposal(self, proposal, company_name):
        """Save proposal to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        slug = company_name.lower().replace(' ', '_').replace('/', '_')
        output_path = self.output_dir / f'{slug}-role-proposal.md'

        with open(output_path, 'w') as f:
            f.write(proposal)

        return output_path
