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

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
