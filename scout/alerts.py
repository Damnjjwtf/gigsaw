"""Alert system for high-value matches.

Sends notifications via webhook (Slack, Discord), email, or local file.
Configurable via env vars: SLACK_WEBHOOK_URL, DISCORD_WEBHOOK_URL, ALERT_EMAIL.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
from scout.config import Config


class AlertSystem:
    """Multi-channel alert dispatcher for high-value matches."""

    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.alert_email = os.getenv('ALERT_EMAIL')
        self.alerts_dir = Path(Config.EXPORT_DIR).parent / 'alerts'
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

    def send_high_value_alert(self, company):
        """Send alert for a high-scoring company across all configured channels."""
        message = self._format_alert(company)
        results = {
            'company': company.get('name'),
            'channels': []
        }

        # Always log locally
        self._log_to_file(company, message)
        results['channels'].append({'channel': 'file', 'status': 'sent'})

        # Send to webhooks if configured
        if self.slack_webhook:
            ok = self._send_slack(message, company)
            results['channels'].append({'channel': 'slack', 'status': 'sent' if ok else 'failed'})

        if self.discord_webhook:
            ok = self._send_discord(message, company)
            results['channels'].append({'channel': 'discord', 'status': 'sent' if ok else 'failed'})

        if self.alert_email:
            # Email would require SMTP config; for now, log it
            self._log_email_target(company, message)
            results['channels'].append({'channel': 'email', 'status': 'queued'})

        return results

    def _format_alert(self, company):
        """Format a company as a markdown alert."""
        name = company.get('name', 'Unknown')
        score = company.get('score', 'N/A')
        grade = company.get('grade', 'N/A')
        stage = company.get('stage', 'unknown')
        amount = company.get('amount_usd', 0)
        rationale = company.get('rationale', '')
        website = company.get('website', '')

        amount_str = f'${amount/1_000_000:.1f}M' if amount and amount >= 1_000_000 else f'${amount:,}' if amount else 'N/A'

        return f"""🎯 *SCOUT High-Value Target*

*{name}* — Score: *{score}/100* [{grade}]
Stage: {stage} | Funding: {amount_str}

{rationale[:300]}

{f"🌐 {website}" if website else ""}

Next: `/scout draft "{name}"` or `/scout wild "{name}"`"""

    def _send_slack(self, message, company):
        """POST to Slack webhook."""
        try:
            response = requests.post(
                self.slack_webhook,
                json={
                    'text': message,
                    'username': 'SCOUT',
                    'icon_emoji': ':dart:'
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f'⚠ Slack alert failed: {e}')
            return False

    def _send_discord(self, message, company):
        """POST to Discord webhook."""
        try:
            response = requests.post(
                self.discord_webhook,
                json={
                    'username': 'SCOUT',
                    'content': message
                },
                timeout=10
            )
            return response.status_code in (200, 204)
        except Exception as e:
            print(f'⚠ Discord alert failed: {e}')
            return False

    def _log_to_file(self, company, message):
        """Append to local alerts log."""
        timestamp = datetime.now().strftime('%Y%m%d')
        alerts_file = self.alerts_dir / f'alerts_{timestamp}.log'

        with open(alerts_file, 'a') as f:
            f.write(f'\n[{datetime.now().isoformat()}] {company.get("name")}\n')
            f.write(message)
            f.write('\n' + '-' * 60 + '\n')

    def _log_email_target(self, company, message):
        """Log emails that would be sent (SMTP not configured)."""
        queue_file = self.alerts_dir / 'email_queue.jsonl'
        with open(queue_file, 'a') as f:
            f.write(json.dumps({
                'to': self.alert_email,
                'subject': f'[SCOUT] High-value target: {company.get("name")}',
                'body': message,
                'timestamp': datetime.now().isoformat(),
                'status': 'queued'
            }) + '\n')

    def status(self):
        """Return configured alert channels."""
        return {
            'slack': bool(self.slack_webhook),
            'discord': bool(self.discord_webhook),
            'email': bool(self.alert_email),
            'file_log': True
        }
