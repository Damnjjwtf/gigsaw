import os
import sys


class Config:
    """Load and validate API credentials from environment."""

    # Required for full functionality
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    CRUNCHBASE_API_KEY = os.getenv('CRUNCHBASE_API_KEY')
    APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')

    # Optional / fallback sources
    DB_PATH = os.getenv('SCOUT_DB_PATH', '/home/user/gigsaw/scout/scout.db')
    EXPORT_DIR = os.getenv('SCOUT_EXPORT_DIR', '/home/user/gigsaw/scout/exports')

    # Model
    CLAUDE_MODEL = 'claude-opus-4-7'

    @staticmethod
    def check():
        """Validate critical credentials. Return True if MVP sources available."""
        # TechCrunch RSS doesn't need any API keys
        # Warn about optional sources
        if not Config.ANTHROPIC_API_KEY:
            print('⚠ ANTHROPIC_API_KEY not set — scoring/drafting disabled')

        if not Config.CRUNCHBASE_API_KEY:
            print('⚠ CRUNCHBASE_API_KEY not set — Crunchbase source disabled')

        if not Config.APIFY_API_TOKEN:
            print('⚠ APIFY_API_TOKEN not set — scraping sources disabled')

        print('✓ TechCrunch feed available (no API key needed)')
        print('✓ Config validated')
        return True

    @staticmethod
    def status():
        """Show configuration status."""
        print('\n--- SCOUT CONFIG ---')
        print(f'ANTHROPIC_API_KEY: {"✓ set" if Config.ANTHROPIC_API_KEY else "✗ missing"}')
        print(f'CRUNCHBASE_API_KEY: {"✓ set" if Config.CRUNCHBASE_API_KEY else "○ optional"}')
        print(f'APIFY_API_TOKEN: {"✓ set" if Config.APIFY_API_TOKEN else "○ optional"}')
        print(f'Database: {Config.DB_PATH}')
        print(f'Exports: {Config.EXPORT_DIR}')
        print('---\n')
