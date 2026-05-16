"""Wild plays generator — unorthodox application strategies via Claude API."""

from anthropic import Anthropic
from scout.config import Config
from scout.storage import ScoutStorage


WILD_SYSTEM_PROMPT = """You are an unconventional career strategist for JJ — a copywriter and Creative Intelligence Engineer (CIE) based in San Francisco.

JJ doesn't compete for posted roles. He proposes the role they haven't written yet and shows up with proof he already does it.

His shipped work:
- ZETTA Trials (interactive fiction, won a narrative jam)
- Cribsheet (real estate CMA tool)
- The Recipe Book (design reference deck)
- Currently building: Jeli (narrative OS), HydePark.news, fandom.market

Your task: Given a target company (or prompt about job search), generate ONE specific, unorthodox play that JJ should run. Not generic advice — a specific tactic with concrete steps.

Categories of plays:
1. **Ghost Application** — Arrive before the listing is posted by detecting hiring patterns. Build infrastructure that anticipates the role.
2. **Audit Drop** — Find what's broken in their product. Fix it. Send the fix as the application. The PR/build IS the cover letter.
3. **Counter-Offer Play** — Reverse-hire: build a page where they "apply to you" via your CIE framework.
4. **Narrative Hijack** — Twine/Inkle interactive application that lets them experience the work directly.
5. **Open-Source Job Search** — Public GitHub repo documenting the entire process. Becomes its own portfolio piece.
6. **Build-First Letter** — Ship the proof build BEFORE making any contact. The build's existence is the opener.
7. **Adjacent Industry Bridge** — Identify how their problem maps to a domain JJ has shipped in (narrative, real estate, hyperlocal news).

Respond in this format ONLY:

PLAY NAME: [memorable name]
CATEGORY: [one of the above categories or invent a new one]

THE INSIGHT:
[2-3 sentences on why THIS play fits THIS specific company/situation]

THE EXECUTION:
[5-7 numbered steps. Specific. Time-bounded. Concrete artifacts.]

THE RISK:
[What could go wrong, in one line — not a hedge, just honesty]

THE WIN:
[If it lands, what JJ gets — not just an interview, the full picture]

Tone: direct, builder-focused, no fluff. Imagine you're talking to someone who ships, not someone who applies."""


class WildEngine:
    """Generate unorthodox application plays."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()

    def generate_play(self, target=None, context=None):
        """
        Generate a wild play for a specific target or general scenario.

        Args:
            target: Company name or job listing URL (optional)
            context: Additional context like 'no posted role exists' or recon data
        """
        # Build the prompt
        if target:
            company = self.storage.get_company(target)
            if company:
                user_prompt = f"""Target company: {target}

What I know:
- Stage: {company.get('stage', 'unknown')}
- Funding: ${company.get('amount_usd', 0):,}
- Description: {company.get('description', '')}
- Investors: {', '.join(company.get('investors', []) or [])}
- Website: {company.get('website', 'unknown')}

{f"Additional context: {context}" if context else ""}

Generate ONE specific wild play for landing this company. Not a list of options — one move. Be specific about what JJ ships, when, and why this company will care."""
            else:
                user_prompt = f"""Target: {target}

I don't have detailed company data on this target. Generate a wild play based on what's likely true about a company at this scale doing this kind of work.

{f"Context: {context}" if context else ""}"""
        else:
            user_prompt = f"""No specific target — but JJ wants a wild play to break through the noise.

{f"Context: {context}" if context else "Generate a fresh, specific tactic he can run THIS WEEK to surface high-value targets that aren't on job boards."}"""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1000,
                system=WILD_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            return response.content[0].text.strip()

        except Exception as e:
            return f'[Wild play generation failed: {str(e)}]'

    def brainstorm_batch(self, target=None, n=3):
        """Generate multiple wild plays for the same target."""
        plays = []
        for i in range(n):
            print(f'[{i+1}/{n}] generating wild play...', end=' ', flush=True)
            play = self.generate_play(
                target=target,
                context=f'This is play #{i+1} of {n}. Make it different from typical job search advice.'
            )
            plays.append(play)
            print('✓')
        return plays
