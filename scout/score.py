"""Score companies against JJ's profile using Claude API."""

import json
from anthropic import Anthropic
from scout.storage import ScoutStorage
from scout.config import Config


SCORING_SYSTEM_PROMPT = """You are a career intelligence system that evaluates startup funding announcements for a specific candidate.

The candidate's profile:
- Name: JJ
- Title: Copywriter & Creative Intelligence Engineer (CIE)
- Background: Recent graduate of The Academy at Goodby Silverstein & Partners (San Francisco)
- Shipped work: ZETTA Trials (interactive fiction), Cribsheet (real estate CMA), The Recipe Book (design reference)
- Current projects: Jeli (narrative OS), HydePark.news (hyperlocal news), fandom.market (belief pricing)
- Location: San Francisco Bay Area
- Target roles: Copywriting, creative strategy, brand narrative, content, AI-adjacent creative work

Your task: Score a recently funded company on how well it maps to this candidate's skills and interests.

Score on a scale of 0-100 with these factors:
1. **Creative Need (0-30):** Does the company need a copywriter, narrative designer, brand strategist, or content lead?
2. **AI Adjacency (0-20):** Is the company building AI tools, using AI internally, or exploring AI-adjacent creative work?
3. **Stage Fit (0-15):** Series A or earlier scores higher (more likely to need generalists). Seed > Series A > Series B > Series C.
4. **Hiring Urgency (0-15):** Recent funding (within 30 days) = high urgency. Scales down by week.
5. **Location Fit (0-10):** Bay Area = 10, California = 7, Remote = 5, Other = 0.
6. **Brand Voice (0-10):** Does the company have a strong public voice, vibrant community, or narrative focus?

Grading:
- 90-100: Perfect fit. Immediate outreach.
- 80-89: Strong fit. High priority.
- 70-79: Good fit. Consider outreach.
- 60-69: Moderate fit. Lower priority.
- 0-59: Weak fit. Not recommended.

Return ONLY valid JSON:
{
  "score": 87,
  "grade": "A",
  "rationale": "Clear explanation of the score",
  "factors": {
    "creative_need": 25,
    "ai_adjacency": 18,
    "stage_fit": 14,
    "hiring_urgency": 12,
    "location_fit": 10,
    "brand_voice": 8
  }
}

Never return markdown, explanations, or anything else. Only JSON."""


class ScoreEngine:
    """Score companies using Claude API."""

    def __init__(self):
        self.client = Anthropic()
        self.storage = ScoutStorage()

    def score_company(self, company_data):
        """
        Score a single company. Returns (score, grade, rationale, factors).
        """
        try:
            # Prepare company summary for Claude
            company_prompt = f"""Score this company for JJ:

NAME: {company_data.get('name')}
STAGE: {company_data.get('stage')}
FUNDING: ${company_data.get('amount_usd', 0):,}
ANNOUNCED: {company_data.get('announced_date')}
DESCRIPTION: {company_data.get('description', 'No description available')}
INVESTORS: {', '.join(company_data.get('investors', [])) or 'Unknown'}
WEBSITE: {company_data.get('website') or 'Unknown'}
LOCATION: {company_data.get('location') or 'Unknown (likely Bay Area)'}"""

            # Call Claude with system prompt
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=500,
                system=SCORING_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": company_prompt
                    }
                ]
            )

            # Parse response
            response_text = response.content[0].text.strip()

            # Extract JSON from response (in case there's any formatting)
            if response_text.startswith('{'):
                result_json = response_text
            else:
                # Try to find JSON in the response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start != -1 and end > start:
                    result_json = response_text[start:end]
                else:
                    raise ValueError("Could not parse JSON from Claude response")

            result = json.loads(result_json)

            # Validate structure
            required_keys = ['score', 'grade', 'rationale', 'factors']
            if not all(key in result for key in required_keys):
                raise ValueError(f"Missing required keys in response: {required_keys}")

            # Save to storage
            self.storage.save_score(
                company_data.get('name'),
                result['score'],
                result['rationale']
            )

            return result

        except json.JSONDecodeError as e:
            return {
                'score': 0,
                'grade': 'F',
                'rationale': f'Failed to parse scoring response: {str(e)}',
                'factors': {}
            }
        except Exception as e:
            return {
                'score': 0,
                'grade': 'F',
                'rationale': f'Scoring error: {str(e)}',
                'factors': {}
            }

    def score_batch(self, companies, min_score=70):
        """
        Score multiple companies. Return only those above min_score threshold.
        """
        results = []
        for i, company in enumerate(companies):
            print(f'[{i+1}/{len(companies)}] Scoring {company.get("name")}...', end='', flush=True)
            result = self.score_company(company)
            if result['score'] >= min_score:
                results.append({
                    **company,
                    'score': result['score'],
                    'grade': result['grade'],
                    'rationale': result['rationale'],
                    'factors': result['factors']
                })
                print(f' {result["grade"]} ({result["score"]})')
            else:
                print(f' F ({result["score"]})')

        return sorted(results, key=lambda x: x['score'], reverse=True)

    def format_score_report(self, company):
        """Format a scored company for display."""
        score = company.get('score', 0)
        grade = company.get('grade', 'F')
        rationale = company.get('rationale', '')
        factors = company.get('factors', {})

        report = f"""
COMPANY: {company.get('name')}
SCORE: {score}/100 [{grade}]
STAGE: {company.get('stage')} | FUNDING: ${company.get('amount_usd', 0):,}

RATIONALE:
{rationale}

FACTOR BREAKDOWN:
  Creative Need:     {factors.get('creative_need', 0)}/30
  AI Adjacency:      {factors.get('ai_adjacency', 0)}/20
  Stage Fit:         {factors.get('stage_fit', 0)}/15
  Hiring Urgency:    {factors.get('hiring_urgency', 0)}/15
  Location Fit:      {factors.get('location_fit', 0)}/10
  Brand Voice:       {factors.get('brand_voice', 0)}/10

DESCRIPTION:
{company.get('description', 'N/A')}

INVESTORS: {', '.join(company.get('investors', [])) or 'N/A'}
WEBSITE: {company.get('website') or 'N/A'}
---
"""
        return report
