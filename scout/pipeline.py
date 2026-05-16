"""Integrate SCOUT results into GIGSAW pipeline."""

import json
import os
from pathlib import Path
from scout.storage import ScoutStorage


class GigsawPipeline:
    """Push SCOUT results to GIGSAW pipeline."""

    def __init__(self):
        self.storage = ScoutStorage()
        self.gigsaw_data_path = Path('/home/user/gigsaw/data')

    def push_company(self, company_data, score_result=None, draft_result=None, inspection_result=None):
        """
        Push a high-value company to GIGSAW pipeline.
        Creates entries for /gigsaw recon and /gigsaw build.
        """
        company_name = company_data.get('name')
        score = score_result.get('score', 0) if score_result else 0

        # Only push companies with strong scores
        if score < 75:
            return False

        print(f'[...] pushing {company_name} to GIGSAW pipeline')

        # Create recon file
        recon_file = self.gigsaw_data_path / 'recon' / f'{company_name.lower().replace(" ", "_")}.md'
        self._create_recon_file(recon_file, company_data, score_result, inspection_result)

        # Add to applications tracker
        self._update_tracker(company_data, score_result)

        print(f'✓ {company_name} pushed to GIGSAW pipeline')
        return True

    def _create_recon_file(self, output_path, company_data, score_result, inspection_result):
        """Create a GIGSAW recon file for a company."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        recon_content = f"""# Recon: {company_data.get('name')}

## Company Overview
- **Stage:** {company_data.get('stage')}
- **Funding:** ${company_data.get('amount_usd', 0):,}
- **Announced:** {company_data.get('announced_date')}
- **Website:** {company_data.get('website') or 'N/A'}
- **Location:** {company_data.get('location') or 'Unknown'}

## Description
{company_data.get('description', 'No description available')}

## Investors
{', '.join(company_data.get('investors', [])) or 'Unknown'}

## SCOUT Assessment
- **Score:** {score_result.get('score', 0)}/100 [{score_result.get('grade', 'F')}]
- **Rationale:** {score_result.get('rationale', 'N/A')}

### Factor Breakdown
{self._format_factors(score_result.get('factors', {}))}

## Hiring Signals
"""
        if inspection_result and inspection_result.get('open_roles'):
            recon_content += f"- **Open Roles:** {', '.join(inspection_result['open_roles'])}\n"
            recon_content += f"- **Hiring Urgency:** {inspection_result.get('hiring_urgency', 'unknown')}\n"
        else:
            recon_content += "- No career page found yet\n"

        recon_content += """
## Next Steps
- [ ] Visit website and explore product
- [ ] Research founding team on LinkedIn
- [ ] Check recent news/announcements
- [ ] Review competitor landscape
- [ ] Identify potential build/proposal angle

## Build Opportunity
Use `/gigsaw build` to propose a proof build for this company.
Use `/gigsaw propose` if considering a role proposal.
"""

        with open(output_path, 'w') as f:
            f.write(recon_content)

    def _format_factors(self, factors):
        """Format scoring factors for display."""
        if not factors:
            return "- No factors available"

        lines = []
        factor_names = {
            'creative_need': 'Creative Need',
            'ai_adjacency': 'AI Adjacency',
            'stage_fit': 'Stage Fit',
            'hiring_urgency': 'Hiring Urgency',
            'location_fit': 'Location Fit',
            'brand_voice': 'Brand Voice'
        }

        for key, name in factor_names.items():
            value = factors.get(key, 0)
            lines.append(f"- **{name}:** {value}")

        return '\n'.join(lines)

    def _update_tracker(self, company_data, score_result):
        """Add company to GIGSAW applications tracker."""
        tracker_file = self.gigsaw_data_path / 'applications.tsv'

        # Ensure file exists with headers
        if not tracker_file.exists():
            tracker_file.parent.mkdir(parents=True, exist_ok=True)
            with open(tracker_file, 'w') as f:
                f.write('date\tcompany\trole\tscore\tgrade\tstatus\turl\twarm_path\tproof_build\tnext_action\tnotes\n')

        # Add entry
        from datetime import datetime
        date_str = datetime.now().strftime('%Y-%m-%d')
        score = score_result.get('score', 0) if score_result else 0
        grade = score_result.get('grade', 'F') if score_result else 'F'

        entry = f"{date_str}\t{company_data.get('name')}\t[TBD]\t{score}\t{grade}\tevaluating\t{company_data.get('website', '')}\t\t\t/gigsaw recon\tFrom SCOUT pipeline\n"

        with open(tracker_file, 'a') as f:
            f.write(entry)

    def export_high_value_targets(self, min_score=80, output_format='json'):
        """Export top-scoring companies for further action."""
        companies = self.storage.get_companies_by_score_range(min_score=min_score, max_score=100)

        if output_format == 'json':
            output_file = self.gigsaw_data_path / f'scout_targets_{min_score}_plus.json'
            with open(output_file, 'w') as f:
                json.dump(companies, f, indent=2)
            return output_file

        return None
