"""Application package generator — tailored resume + cover letter per target.

Pulls profile data, target context, and arbitrage notes to generate a complete
application package. Resume foregrounds proof builds. Cover letter reads like
a builder's letter, not an applicant's plea.
"""

import json
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
from scout.config import Config
from scout.storage import ScoutStorage


PROFILE_PATH = Path(__file__).parent.parent / 'profile.json'


RESUME_SYSTEM_PROMPT = """You are generating a tailored resume for JJ targeting a specific company.

JJ's positioning:
- Copywriter & Creative Intelligence Engineer (CIE)
- Recent graduate of The Academy at Goodby Silverstein & Partners
- Shipped: ZETTA Trials (interactive fiction, won a narrative jam), Cribsheet (real estate CMA tool), The Recipe Book (design reference deck)
- Building: Jeli (narrative OS), HydePark.news (hyperlocal news aggregator), fandom.market (belief pricing engine)
- Based in San Francisco, with production connections in Chicago and New York

CRITICAL CONSTRAINTS:
1. NEVER fabricate experience, skills, or credentials. Only use what's true about JJ.
2. Reorder shipped work and experience for relevance to THIS company.
3. If a proof build for this company exists, lead the resume with it under "Built for [Company]".
4. Every shipped project must have a live URL. Flag if a URL is missing.
5. Skills section comes AFTER shipped work, not before — JJ's resume shows what he's done, not what he claims he can do.

Output: a complete Markdown resume.

Structure:
1. Header (name, title, location, links)
2. PROOF BUILD section — only if applicable: "Built for [Company]"
3. SHIPPED — 3-5 most relevant projects with live URLs
4. EXPERIENCE — work history reordered by relevance
5. SKILLS & TOOLS
6. EDUCATION

Keep it dense. One page when printed."""


COVER_SYSTEM_PROMPT = """You are writing a cover letter from JJ targeting a specific company.

JJ's positioning:
- Copywriter & Creative Intelligence Engineer (CIE) — a category he coined
- Combines narrative systems, AI-assisted creative work, copywriting, screenwriting, brand strategy
- Recent graduate of The Academy at Goodby Silverstein & Partners
- Shipped: ZETTA Trials, Cribsheet, The Recipe Book

CRITICAL CONSTRAINTS:
1. This reads like a BUILDER'S LETTER, not an applicant's plea.
2. Open with the specific problem you noticed at this company OR the arbitrage insight (where the role is heading).
3. NEVER use phrases like "I'm excited to apply" or "I would love the opportunity."
4. If a proof build exists, structure: (1) what you noticed, (2) what you built, (3) what you'd build next.
5. Never fabricate. If you don't know something, don't claim it.
6. End with something concrete — a specific next step, not "looking forward to hearing from you."
7. 250-350 words MAX.

Output: pure cover letter text. No headers, no metadata."""


class RemixEngine:
    """Generate tailored application packages."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()
        self.output_root = Path(__file__).parent.parent / 'output'

    def remix(self, company_name, role=None, proof_build=None, arbitrage_notes=None):
        """
        Generate a full application package: resume + cover letter + portfolio selection.

        Args:
            company_name: Target company
            role: Specific role title (optional)
            proof_build: Path to a proof build directory (optional)
            arbitrage_notes: Arbitrage analysis text (optional)
        """
        # Load profile
        profile = self._load_profile()
        if not profile:
            return {
                'success': False,
                'error': f'No profile.json at {PROFILE_PATH}. Run /gigsaw setup first.',
                'company': company_name
            }

        # Get company context
        company = self.storage.get_company(company_name)
        if not company:
            return {
                'success': False,
                'error': f'Company {company_name} not found in database.',
                'company': company_name
            }

        # Build the output directory
        slug = company_name.lower().replace(' ', '_').replace('/', '_')
        if role:
            slug += f'_{role.lower().replace(" ", "_")}'
        output_dir = self.output_root / slug
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate resume
        resume_md = self._generate_resume(profile, company, role, proof_build)
        (output_dir / 'resume.md').write_text(resume_md)

        # Generate cover letter
        cover_md = self._generate_cover(profile, company, role, proof_build, arbitrage_notes)
        (output_dir / 'cover-letter.md').write_text(cover_md)

        # Generate portfolio selection
        portfolio_md = self._generate_portfolio_selection(profile, company, role)
        (output_dir / 'portfolio-selection.md').write_text(portfolio_md)

        # Generate match assessment
        assessment = self._generate_match_assessment(profile, company, role)
        (output_dir / 'match-assessment.json').write_text(json.dumps(assessment, indent=2))

        return {
            'success': True,
            'company': company_name,
            'role': role,
            'output_dir': str(output_dir),
            'files': ['resume.md', 'cover-letter.md', 'portfolio-selection.md', 'match-assessment.json']
        }

    def _load_profile(self):
        """Load profile.json or return a default profile based on CLAUDE.md."""
        if PROFILE_PATH.exists():
            try:
                return json.loads(PROFILE_PATH.read_text())
            except Exception:
                pass

        # Default profile from CLAUDE.md if profile.json missing
        return {
            'name': 'JJ',
            'title': 'Copywriter & Creative Intelligence Engineer',
            'location': 'San Francisco Bay Area',
            'shipped_work': [
                {
                    'title': 'ZETTA Trials',
                    'description': 'Interactive fiction',
                    'proves': 'Narrative systems + interactive design',
                    'url': '[ZETTA URL]',
                    'achievement': 'Won a narrative jam'
                },
                {
                    'title': 'Cribsheet',
                    'description': 'Real estate CMA tool',
                    'proves': 'Builds tools that ship',
                    'url': '[Cribsheet URL]'
                },
                {
                    'title': 'The Recipe Book',
                    'description': 'Design reference deck',
                    'proves': 'Curatorial design thinking',
                    'url': '[Recipe Book URL]'
                }
            ],
            'building': [
                {'title': 'Jeli', 'description': 'Narrative OS'},
                {'title': 'HydePark.news', 'description': 'Hyperlocal news aggregator'},
                {'title': 'fandom.market', 'description': 'Belief pricing engine'}
            ],
            'education': [
                {
                    'institution': 'The Academy at Goodby Silverstein & Partners',
                    'location': 'San Francisco',
                    'date': 'Recent graduate'
                }
            ]
        }

    def _generate_resume(self, profile, company, role, proof_build):
        """Generate tailored resume."""
        prompt = f"""Generate a resume for JJ targeting:

COMPANY: {company.get('name')}
ROLE: {role or '[Tailor for general fit]'}
COMPANY DESCRIPTION: {company.get('description', '')}
COMPANY STAGE: {company.get('stage', '')}

JJ'S PROFILE:
{json.dumps(profile, indent=2)}

{f"PROOF BUILD FOR {company.get('name').upper()}: {proof_build}" if proof_build else "No proof build for this company yet."}

Generate the full Markdown resume."""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=2000,
                system=RESUME_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f'[Resume generation failed: {str(e)}]'

    def _generate_cover(self, profile, company, role, proof_build, arbitrage_notes):
        """Generate tailored cover letter."""
        prompt = f"""Write a cover letter for JJ targeting:

COMPANY: {company.get('name')}
ROLE: {role or '[General fit]'}
COMPANY DESCRIPTION: {company.get('description', '')}
COMPANY STAGE: {company.get('stage', '')}

JJ'S PROFILE:
{json.dumps(profile, indent=2)}

{f"PROOF BUILD: {proof_build}" if proof_build else ""}

{f"ARBITRAGE INSIGHT: {arbitrage_notes}" if arbitrage_notes else ""}

Write a 250-350 word builder's letter."""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=800,
                system=COVER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f'[Cover letter generation failed: {str(e)}]'

    def _generate_portfolio_selection(self, profile, company, role):
        """Pick the best 3 projects to highlight for this target."""
        prompt = f"""Pick the 3 most relevant shipped projects from JJ's portfolio for this application.

COMPANY: {company.get('name')}
ROLE: {role or '[General fit]'}
COMPANY DESCRIPTION: {company.get('description', '')}

JJ'S SHIPPED WORK:
{json.dumps(profile.get('shipped_work', []), indent=2)}

Output as Markdown:

# Portfolio Selection: {company.get('name')}

For each of the top 3 picks:

## [Project Title]
**Why this one:** [1 sentence on relevance to THIS target]
**What it proves:** [1 sentence]
**URL:** [from profile]

Keep total under 250 words."""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f'[Portfolio selection failed: {str(e)}]'

    def _generate_match_assessment(self, profile, company, role):
        """Generate a structured match assessment."""
        prompt = f"""Assess how well JJ matches this opportunity. Return ONLY JSON.

COMPANY: {company.get('name')}
ROLE: {role or 'general fit'}
DESCRIPTION: {company.get('description', '')}

JJ'S PROFILE:
{json.dumps(profile, indent=2)}

Return ONLY valid JSON in this format:
{{
  "fit_score": 0-100,
  "strongest_match_signals": ["signal 1", "signal 2", "signal 3"],
  "weakest_areas": ["area 1", "area 2"],
  "honest_gaps": ["thing JJ doesn't have", "thing JJ doesn't have"],
  "recommendation": "apply" | "build_first" | "propose" | "skip" | "watch",
  "reasoning": "1-2 sentences"
}}"""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()

            # Strip markdown code fences if present
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]

            return json.loads(text)
        except Exception as e:
            return {
                'fit_score': 0,
                'recommendation': 'skip',
                'reasoning': f'Assessment failed: {str(e)}'
            }
