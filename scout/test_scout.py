#!/usr/bin/env python3

"""Comprehensive test suite for SCOUT Phase 2."""

import unittest
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path

from scout.config import Config
from scout.storage import ScoutStorage
from scout.feed import Feed
from scout.score import ScoreEngine
from scout.draft import DraftEngine
from scout.careers import CareerPageInspector
from scout.pipeline import GigsawPipeline
from scout.wild import WildEngine
from scout.dashboard import Dashboard
from scout.digest import DigestGenerator
from scout.sources.hackernews import HackerNewsSource
from scout.sources.apify_source import ApifyScraper
from scout.arbitrage import ArbitrageEngine
from scout.propose import ProposeEngine
from scout.who import NetworkScanner
from scout.recon import ReconEngine
from scout.watch import Watcher
from scout.alerts import AlertSystem
from scout.remix import RemixEngine
from scout.web import WebQueries, render_dashboard, render_companies, render_runs, render_company, page, score_class, fmt_amount


class TestStorage(unittest.TestCase):
    """Test SQLite storage layer."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Patch Config to use temp db
        original_db = Config.DB_PATH
        Config.DB_PATH = self.db_path
        self.original_db = original_db

        self.storage = ScoutStorage()

    def tearDown(self):
        Config.DB_PATH = self.original_db
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_insert_company(self):
        """Test company insertion."""
        company = {
            'name': 'Test Company',
            'website': 'https://test.com',
            'description': 'A test company',
            'stage': 'Series A',
            'amount_usd': 5_000_000,
            'announced_date': datetime.now().isoformat(),
            'source': 'test'
        }

        inserted = self.storage.insert_company(company)
        self.assertTrue(inserted)

        # Try inserting duplicate
        inserted_again = self.storage.insert_company(company)
        self.assertFalse(inserted_again)  # Should return False for duplicate

    def test_get_company(self):
        """Test company retrieval."""
        company = {
            'name': 'Get Test',
            'website': 'https://test.com',
            'stage': 'Seed',
            'amount_usd': 1_000_000,
            'announced_date': datetime.now().isoformat(),
            'source': 'test'
        }

        self.storage.insert_company(company)
        retrieved = self.storage.get_company('Get Test')

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['name'], 'Get Test')
        self.assertEqual(retrieved['stage'], 'Seed')

    def test_save_score(self):
        """Test score storage."""
        company = {
            'name': 'Score Test',
            'stage': 'Series B',
            'amount_usd': 10_000_000,
            'announced_date': datetime.now().isoformat(),
            'source': 'test'
        }

        self.storage.insert_company(company)
        self.storage.save_score('Score Test', 85, 'Strong fit')

        # Retrieve and verify
        retrieved = self.storage.get_company('Score Test')
        self.assertIsNotNone(retrieved)

    def test_save_draft(self):
        """Test draft storage."""
        company = {
            'name': 'Draft Test',
            'stage': 'Seed',
            'amount_usd': 500_000,
            'announced_date': datetime.now().isoformat(),
            'source': 'test'
        }

        self.storage.insert_company(company)
        self.storage.save_draft(
            'Draft Test',
            'Congrats on funding!',
            'Great work on the raise...',
            tone='warm'
        )

        draft = self.storage.get_draft('Draft Test')
        self.assertIsNotNone(draft)
        self.assertEqual(draft['subject'], 'Congrats on funding!')

    def test_save_inspection(self):
        """Test inspection storage."""
        company = {
            'name': 'Inspect Test',
            'stage': 'Series A',
            'amount_usd': 3_000_000,
            'announced_date': datetime.now().isoformat(),
            'source': 'test'
        }

        self.storage.insert_company(company)
        self.storage.save_inspection(
            'Inspect Test',
            ['Engineer', 'Designer'],
            15,
            'hiring@company.com',
            'high'
        )

        inspection = self.storage.get_inspection('Inspect Test')
        self.assertIsNotNone(inspection)
        self.assertEqual(inspection['hiring_urgency'], 'high')
        self.assertIn('Engineer', inspection['open_roles'])

    def test_get_by_score_range(self):
        """Test querying by score range."""
        for i in range(3):
            company = {
                'name': f'Score Range Test {i}',
                'stage': 'Seed',
                'amount_usd': 1_000_000,
                'announced_date': datetime.now().isoformat(),
                'source': 'test'
            }
            self.storage.insert_company(company)
            self.storage.save_score(company['name'], 70 + (i * 10), 'Test')

        high_score = self.storage.get_companies_by_score_range(min_score=80, max_score=100)
        self.assertGreaterEqual(len(high_score), 1)


class TestFeed(unittest.TestCase):
    """Test data source integration."""

    def setUp(self):
        self.feed = Feed()

    def test_sample_data_fetch(self):
        """Test sample data fetch."""
        companies = self.feed.fetch_sample_data()

        self.assertGreater(len(companies), 0)
        self.assertIn('name', companies[0])
        self.assertIn('stage', companies[0])
        self.assertIn('amount_usd', companies[0])

    def test_yc_fetch(self):
        """Test Y Combinator source."""
        companies = self.feed.fetch_yc_companies()

        self.assertGreater(len(companies), 0)
        for company in companies:
            self.assertEqual(company['source'], 'yc')

    def test_sequoia_fetch(self):
        """Test Sequoia source."""
        companies = self.feed.fetch_sequoia_companies()

        self.assertGreater(len(companies), 0)
        for company in companies:
            self.assertEqual(company['source'], 'sequoia')

    def test_fetch_all(self):
        """Test orchestrated fetch."""
        companies = self.feed.fetch_all(sources=['yc', 'sequoia'])

        self.assertGreater(len(companies), 0)
        sources = set(c.get('source') for c in companies)
        self.assertTrue(sources.issubset({'yc', 'sequoia'}))


class TestScoreEngine(unittest.TestCase):
    """Test scoring via Claude API."""

    def setUp(self):
        if not Config.ANTHROPIC_API_KEY:
            self.skipTest('ANTHROPIC_API_KEY not set')
        self.scorer = ScoreEngine()

    def test_score_company_format(self):
        """Test score format and structure."""
        company = {
            'name': 'Test AI Company',
            'stage': 'Series A',
            'amount_usd': 5_000_000,
            'announced_date': datetime.now().isoformat(),
            'description': 'Building AI tools for content creation',
            'investors': ['Benchmark'],
            'website': 'https://test.com'
        }

        result = self.scorer.score_company(company)

        # Verify structure
        self.assertIn('score', result)
        self.assertIn('grade', result)
        self.assertIn('rationale', result)
        self.assertIn('factors', result)

        # Verify ranges
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)
        # Grade can be A, B, C, D, F, or with modifiers like A+, B-
        grade_letter = result['grade'][0] if result['grade'] else ''
        self.assertIn(grade_letter, ['A', 'B', 'C', 'D', 'F'])

    def test_score_batch(self):
        """Test batch scoring."""
        companies = [
            {
                'name': f'Test Company {i}',
                'stage': 'Series A',
                'amount_usd': 5_000_000,
                'announced_date': datetime.now().isoformat(),
                'description': f'Company {i}',
                'investors': [],
                'website': f'https://test{i}.com'
            }
            for i in range(2)
        ]

        results = self.scorer.score_batch(companies, min_score=0)

        self.assertEqual(len(results), 2)
        for company in results:
            self.assertIn('score', company)
            self.assertIn('grade', company)


class TestDraftEngine(unittest.TestCase):
    """Test outreach draft generation."""

    def setUp(self):
        if not Config.ANTHROPIC_API_KEY:
            self.skipTest('ANTHROPIC_API_KEY not set')
        self.drafter = DraftEngine()

    def test_generate_draft_format(self):
        """Test draft format."""
        company = {
            'name': 'Test Startup',
            'stage': 'Series A',
            'amount_usd': 5_000_000,
            'announced_date': datetime.now().isoformat(),
            'description': 'Building creative AI tools',
            'investors': ['a16z'],
            'website': 'https://teststartup.com'
        }

        draft = self.drafter.generate_draft(company)

        self.assertIn('subject', draft)
        self.assertIn('body', draft)
        self.assertIn('tone', draft)

        self.assertTrue(len(draft['subject']) > 0)
        self.assertTrue(len(draft['body']) > 0)
        self.assertEqual(draft['tone'], 'warm')


class TestCareerPageInspector(unittest.TestCase):
    """Test career page inspection."""

    def setUp(self):
        self.inspector = CareerPageInspector()

    def test_inspect_empty_website(self):
        """Test inspection with no website."""
        company = {
            'name': 'No Website Corp',
            'website': None,
            'stage': 'Seed'
        }

        result = self.inspector.inspect_company(company)

        self.assertEqual(result['open_roles'], [])
        self.assertEqual(result['hiring_urgency'], 'unknown')

    def test_detect_roles_in_html(self):
        """Test role detection in HTML."""
        html = """
        <h1>Join our team</h1>
        <p>Senior Engineer needed</p>
        <p>Product Manager role available</p>
        <p>Marketing and Sales positions</p>
        """

        roles = self.inspector._detect_roles_in_html(html)

        self.assertGreater(len(roles), 0)
        self.assertTrue(any('engineer' in r.lower() for r in roles))


class TestPipeline(unittest.TestCase):
    """Test GIGSAW integration."""

    def setUp(self):
        self.pipeline = GigsawPipeline()
        # Ensure data directories exist
        self.pipeline.gigsaw_data_path.mkdir(parents=True, exist_ok=True)
        (self.pipeline.gigsaw_data_path / 'recon').mkdir(parents=True, exist_ok=True)

    def test_format_factors(self):
        """Test factor formatting."""
        factors = {
            'creative_need': 25,
            'ai_adjacency': 18,
            'stage_fit': 14,
            'hiring_urgency': 12,
            'location_fit': 10,
            'brand_voice': 8
        }

        formatted = self.pipeline._format_factors(factors)

        self.assertIn('Creative Need', formatted)
        self.assertIn('AI Adjacency', formatted)
        self.assertIn('25', formatted)

    def test_create_recon_file(self):
        """Test recon file creation."""
        company = {
            'name': 'Recon Test Company',
            'stage': 'Series B',
            'amount_usd': 10_000_000,
            'announced_date': datetime.now().isoformat(),
            'description': 'Test description',
            'website': 'https://test.com',
            'location': 'San Francisco, CA',
            'investors': ['Test VC']
        }

        score_result = {
            'score': 85,
            'grade': 'A',
            'rationale': 'Strong fit',
            'factors': {
                'creative_need': 25,
                'ai_adjacency': 18,
                'stage_fit': 14,
                'hiring_urgency': 12,
                'location_fit': 10,
                'brand_voice': 8
            }
        }

        output_path = self.pipeline.gigsaw_data_path / 'recon' / 'test_company.md'

        self.pipeline._create_recon_file(output_path, company, score_result, None)

        self.assertTrue(output_path.exists())
        with open(output_path) as f:
            content = f.read()
            self.assertIn('Recon Test Company', content)
            self.assertIn('85', content)


class TestHackerNewsSource(unittest.TestCase):
    """Test Hacker News Who's Hiring parser."""

    def setUp(self):
        self.source = HackerNewsSource()

    def test_sample_companies_format(self):
        """Test sample data structure."""
        companies = self.source._sample_hiring_companies()
        self.assertGreater(len(companies), 0)

        for c in companies:
            self.assertIn('name', c)
            self.assertIn('source', c)
            self.assertEqual(c['source'], 'hackernews')
            self.assertIn('open_roles', c)
            self.assertIsInstance(c['open_roles'], list)

    def test_parse_hiring_post(self):
        """Test parsing a single HN comment into a company."""
        comment = {
            'id': 12345,
            'text': '<p>Replicate | SF | Senior Engineer | Onsite</p><p>We are hiring engineers and designers.</p><p>https://replicate.com</p>'
        }
        thread_data = {'time': 1700000000}

        company = self.source._parse_hiring_post(comment, thread_data)

        self.assertIsNotNone(company)
        self.assertEqual(company['name'], 'Replicate')
        self.assertIn('SF', company.get('location', '') or '')

    def test_skip_short_posts(self):
        """Posts that are too short should be skipped."""
        comment = {'id': 1, 'text': 'too short'}
        thread_data = {'time': 1700000000}

        result = self.source._parse_hiring_post(comment, thread_data)
        self.assertIsNone(result)


class TestApifyScraper(unittest.TestCase):
    """Test Apify scraper with sample data fallback."""

    def setUp(self):
        self.scraper = ApifyScraper()

    def test_yc_sample_fallback(self):
        """Test YC sample data when no token."""
        # Force fallback by clearing token
        original_token = self.scraper.token
        self.scraper.token = None

        try:
            companies = self.scraper.fetch_yc_companies()
            self.assertGreater(len(companies), 0)
            for c in companies:
                self.assertEqual(c['source'], 'yc')
                self.assertIn('name', c)
        finally:
            self.scraper.token = original_token

    def test_sequoia_sample_fallback(self):
        """Test Sequoia sample data when no token."""
        original_token = self.scraper.token
        self.scraper.token = None

        try:
            companies = self.scraper.fetch_sequoia_companies()
            self.assertGreater(len(companies), 0)
            for c in companies:
                self.assertEqual(c['source'], 'sequoia')
        finally:
            self.scraper.token = original_token


class TestWildEngine(unittest.TestCase):
    """Test wild plays generator."""

    def setUp(self):
        if not Config.ANTHROPIC_API_KEY:
            self.skipTest('ANTHROPIC_API_KEY not set')
        self.engine = WildEngine()

    def test_generate_play_no_target(self):
        """Test generating a play without specific target."""
        play = self.engine.generate_play(target=None)
        self.assertIsInstance(play, str)
        self.assertGreater(len(play), 50)

    def test_generate_play_with_unknown_target(self):
        """Test generating a play for an unknown target."""
        play = self.engine.generate_play(target='SomeUnknownStartup')
        self.assertIsInstance(play, str)
        self.assertGreater(len(play), 50)


class TestDashboard(unittest.TestCase):
    """Test pipeline dashboard."""

    def setUp(self):
        self.dashboard = Dashboard()

    def test_render_returns_string(self):
        """Test dashboard renders a string."""
        output = self.dashboard.render()
        self.assertIsInstance(output, str)
        self.assertIn('SCOUT DASHBOARD', output)
        self.assertIn('PIPELINE', output)

    def test_gather_stats_structure(self):
        """Test stats dictionary structure."""
        stats = self.dashboard._gather_stats()

        required_keys = ['total_companies', 'recent_companies', 'scored',
                         'drafted', 'inspected', 'score_buckets',
                         'top_targets', 'recent_runs']
        for key in required_keys:
            self.assertIn(key, stats)

    def test_suggest_actions_empty_pipeline(self):
        """Test suggestions when pipeline is empty."""
        empty_stats = {
            'total_companies': 0,
            'recent_companies': 0,
            'scored': 0,
            'top_targets': []
        }
        actions = self.dashboard._suggest_actions(empty_stats)
        self.assertGreater(len(actions), 0)
        self.assertTrue(any('feed' in a.lower() for a in actions))


class TestDigestGenerator(unittest.TestCase):
    """Test daily digest generation."""

    def setUp(self):
        self.generator = DigestGenerator()

    def test_empty_digest(self):
        """Test digest output when no scores exist."""
        result = self.generator._empty_digest()
        self.assertIsInstance(result, str)
        self.assertIn('SCOUT DIGEST', result)
        self.assertIn('Action Queue', result)


class TestArbitrageEngine(unittest.TestCase):
    """Test arbitrage analysis."""

    def setUp(self):
        if not Config.ANTHROPIC_API_KEY:
            self.skipTest('ANTHROPIC_API_KEY not set')
        self.engine = ArbitrageEngine()

    def test_analyze_returns_report(self):
        """Test arbitrage returns a structured report."""
        result = self.engine.analyze(
            'Senior Brand Designer needed. Lead our brand voice and visual identity.',
            company_name=None
        )

        self.assertIn('report', result)
        self.assertIn('timestamp', result)
        self.assertGreater(len(result['report']), 100)


class TestProposeEngine(unittest.TestCase):
    """Test role proposal generation."""

    def setUp(self):
        if not Config.ANTHROPIC_API_KEY:
            self.skipTest('ANTHROPIC_API_KEY not set')
        self.engine = ProposeEngine()

    def test_generate_proposal_format(self):
        """Test proposal output structure."""
        result = self.engine.generate_proposal('TestCorp')

        self.assertIn('proposal', result)
        self.assertIn('company', result)
        self.assertEqual(result['company'], 'TestCorp')


class TestNetworkScanner(unittest.TestCase):
    """Test LinkedIn connection cross-reference."""

    def setUp(self):
        self.scanner = NetworkScanner()

    def test_no_connections_file(self):
        """Test graceful handling when connections.csv doesn't exist."""
        # Temporarily point to a non-existent file
        original = self.scanner.connections_path
        self.scanner.connections_path = Path('/nonexistent/path/connections.csv')

        try:
            result = self.scanner.find_connections_at('AnyCompany')
            self.assertIn('error', result)
            self.assertEqual(result.get('connections', []), [])
        finally:
            self.scanner.connections_path = original

    def test_report_no_file(self):
        """Test report formatting without connections file."""
        original = self.scanner.connections_path
        self.scanner.connections_path = Path('/nonexistent/path/connections.csv')

        try:
            output = self.scanner.report('AnyCompany')
            self.assertIsInstance(output, str)
            self.assertIn('AnyCompany', output)
        finally:
            self.scanner.connections_path = original


class TestReconEngine(unittest.TestCase):
    """Test recon brief generation."""

    def setUp(self):
        if not Config.ANTHROPIC_API_KEY:
            self.skipTest('ANTHROPIC_API_KEY not set')
        self.engine = ReconEngine()

    def test_recon_unknown_company(self):
        """Test recon on unknown company returns error gracefully."""
        result = self.engine.deep_dive('NonexistentCompanyXYZ123')

        self.assertIn('report', result)
        self.assertEqual(result.get('success'), False)


class TestWatcher(unittest.TestCase):
    """Test scheduler/watch system."""

    def setUp(self):
        self.watcher = Watcher()

    def test_install_cron_returns_string(self):
        """Test cron line generation."""
        line = self.watcher.install_cron(frequency='daily')
        self.assertIsInstance(line, str)
        self.assertIn('scout.cli', line)
        self.assertIn('watch', line)

    def test_install_launchd_returns_plist(self):
        """Test launchd plist generation."""
        plist = self.watcher.install_launchd()
        self.assertIsInstance(plist, str)
        self.assertIn('<plist', plist)
        self.assertIn('com.gigsaw.scout.watch', plist)


class TestAlertSystem(unittest.TestCase):
    """Test alert dispatching."""

    def setUp(self):
        self.alerts = AlertSystem()

    def test_status_returns_dict(self):
        """Test status method returns expected keys."""
        status = self.alerts.status()
        self.assertIn('slack', status)
        self.assertIn('discord', status)
        self.assertIn('email', status)
        self.assertIn('file_log', status)
        self.assertTrue(status['file_log'])  # Always on

    def test_format_alert(self):
        """Test alert message formatting."""
        company = {
            'name': 'TestCorp',
            'score': 85,
            'grade': 'B',
            'stage': 'Series A',
            'amount_usd': 5_000_000,
            'rationale': 'Strong fit for creative work',
            'website': 'https://test.com'
        }
        message = self.alerts._format_alert(company)
        self.assertIn('TestCorp', message)
        self.assertIn('85', message)
        self.assertIn('B', message)

    def test_log_to_file(self):
        """Test that alerts get logged to local file."""
        company = {
            'name': 'LogTest',
            'score': 90,
            'grade': 'A',
            'stage': 'Seed',
            'amount_usd': 1_000_000,
            'rationale': 'Test',
            'website': ''
        }
        message = self.alerts._format_alert(company)
        self.alerts._log_to_file(company, message)

        # Verify the alert file was written
        timestamp = datetime.now().strftime('%Y%m%d')
        alert_file = self.alerts.alerts_dir / f'alerts_{timestamp}.log'
        self.assertTrue(alert_file.exists())


class TestRemixEngine(unittest.TestCase):
    """Test application package generator."""

    def setUp(self):
        self.engine = RemixEngine()

    def test_load_profile_fallback(self):
        """Test profile loading falls back to default when missing."""
        original = self.engine
        # Temporarily override the path
        from scout import remix
        original_path = remix.PROFILE_PATH
        remix.PROFILE_PATH = Path('/nonexistent/profile.json')

        try:
            profile = self.engine._load_profile()
            self.assertIn('name', profile)
            self.assertIn('shipped_work', profile)
            self.assertGreater(len(profile['shipped_work']), 0)
        finally:
            remix.PROFILE_PATH = original_path

    def test_remix_unknown_company(self):
        """Test remix gracefully handles unknown company."""
        result = self.engine.remix('NonexistentCompanyXYZ987')
        self.assertEqual(result.get('success'), False)
        self.assertIn('error', result)


class TestWeb(unittest.TestCase):
    """Test web dashboard rendering and queries."""

    def setUp(self):
        self.q = WebQueries()

    def test_score_class_buckets(self):
        self.assertEqual(score_class(95), 'high')
        self.assertEqual(score_class(70), 'med')
        self.assertEqual(score_class(20), 'low')
        self.assertEqual(score_class(None), 'low')

    def test_fmt_amount(self):
        self.assertEqual(fmt_amount(None), '-')
        self.assertEqual(fmt_amount(0), '-')
        self.assertEqual(fmt_amount(2_500_000), '$2.5M')
        self.assertEqual(fmt_amount(750_000), '$750K')

    def test_stats_returns_dict(self):
        s = self.q.stats()
        for key in ('total', 'scored', 'high', 'drafted', 'inspected', 'last_run'):
            self.assertIn(key, s)

    def test_score_distribution_buckets(self):
        d = self.q.score_distribution()
        self.assertEqual(set(d.keys()), {'80-100', '60-79', '40-59', '0-39'})
        for v in d.values():
            self.assertGreaterEqual(v, 0)

    def test_dashboard_renders_html(self):
        html_str = render_dashboard(self.q)
        self.assertIn('<!DOCTYPE html>', html_str)
        self.assertIn('SCOUT', html_str)
        self.assertIn('Pipeline Status', html_str)

    def test_companies_renders_html(self):
        html_str = render_companies(self.q)
        self.assertIn('All Companies', html_str)
        self.assertIn('<table>', html_str)

    def test_runs_renders_html(self):
        html_str = render_runs(self.q)
        self.assertIn('Pipeline Runs', html_str)

    def test_company_unknown_returns_404(self):
        content, status = render_company(self.q, 'NonexistentCompanyXYZ987')
        self.assertEqual(status, 404)
        self.assertIn('not in database', content)

    def test_page_escapes_title(self):
        html_str = page('<script>alert(1)</script>', '<p>body</p>')
        self.assertNotIn('<script>alert(1)</script>', html_str)
        self.assertIn('&lt;script&gt;', html_str)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestStorage))
    suite.addTests(loader.loadTestsFromTestCase(TestFeed))
    suite.addTests(loader.loadTestsFromTestCase(TestScoreEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestDraftEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestCareerPageInspector))
    suite.addTests(loader.loadTestsFromTestCase(TestPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestHackerNewsSource))
    suite.addTests(loader.loadTestsFromTestCase(TestApifyScraper))
    suite.addTests(loader.loadTestsFromTestCase(TestWildEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestDashboard))
    suite.addTests(loader.loadTestsFromTestCase(TestDigestGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestArbitrageEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestProposeEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestNetworkScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestReconEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestWatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestAlertSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestRemixEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestWeb))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
