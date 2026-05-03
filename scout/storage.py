import sqlite3
import json
from datetime import datetime
from pathlib import Path
from scout.config import Config


class ScoutStorage:
    """SQLite persistence layer for startup data."""

    def __init__(self):
        self.db_path = Config.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self):
        """Create schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    website TEXT,
                    description TEXT,
                    stage TEXT,
                    amount_usd INTEGER,
                    announced_date TEXT,
                    investors TEXT,
                    headcount INTEGER,
                    source TEXT,
                    last_fetched TEXT,
                    raw_data TEXT,
                    career_page TEXT,
                    location TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    companies_found INTEGER,
                    companies_new INTEGER,
                    status TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    score INTEGER,
                    grade TEXT,
                    rationale TEXT,
                    factors TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(company_name) REFERENCES companies(name)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    subject TEXT,
                    body TEXT,
                    tone TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(company_name) REFERENCES companies(name)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS inspections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    open_roles TEXT,
                    team_size INTEGER,
                    hiring_team TEXT,
                    hiring_urgency TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(company_name) REFERENCES companies(name)
                )
            ''')
            conn.commit()

    def insert_company(self, company_data):
        """Insert or update a company. Returns (inserted, company_id)."""
        now = datetime.now().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO companies
                    (name, website, description, stage, amount_usd, announced_date, investors, headcount, source, last_fetched, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_data.get('name'),
                    company_data.get('website'),
                    company_data.get('description'),
                    company_data.get('stage'),
                    company_data.get('amount_usd'),
                    company_data.get('announced_date'),
                    json.dumps(company_data.get('investors', [])),
                    company_data.get('headcount'),
                    company_data.get('source'),
                    now,
                    json.dumps(company_data)
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Company already exists, update last_fetched
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('UPDATE companies SET last_fetched = ? WHERE name = ?', (now, company_data.get('name')))
                conn.commit()
            return False

    def log_run(self, source, companies_found, companies_new, status='success'):
        """Log a fetch run."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO runs (timestamp, source, companies_found, companies_new, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (now, source, companies_found, companies_new, status))
            conn.commit()

    def save_score(self, company_name, score, rationale):
        """Save a company score."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO scores (company_name, score, rationale, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (company_name, score, rationale, now))
            conn.commit()

    def get_all_companies(self, limit=None):
        """Fetch all companies. Returns list of dicts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = 'SELECT * FROM companies ORDER BY announced_date DESC'
            if limit:
                query += f' LIMIT {limit}'
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def get_company(self, name):
        """Fetch a specific company."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute('SELECT * FROM companies WHERE name = ?', (name,)).fetchone()
            return dict(row) if row else None

    def get_recent_companies(self, days=60):
        """Fetch companies announced in last N days."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT * FROM companies
                WHERE datetime(announced_date) >= datetime('now', '-' || ? || ' days')
                ORDER BY announced_date DESC
            ''', (days,)).fetchall()
            return [dict(row) for row in rows]

    def save_draft(self, company_name, subject, body, tone='warm'):
        """Save a cold outreach draft."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO drafts (company_name, subject, body, tone, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (company_name, subject, body, tone, now))
            conn.commit()

    def get_draft(self, company_name):
        """Fetch the latest draft for a company."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute('''
                SELECT * FROM drafts WHERE company_name = ? ORDER BY timestamp DESC LIMIT 1
            ''', (company_name,)).fetchone()
            return dict(row) if row else None

    def save_inspection(self, company_name, open_roles, team_size, hiring_team, hiring_urgency):
        """Save career page inspection results."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO inspections (company_name, open_roles, team_size, hiring_team, hiring_urgency, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (company_name, json.dumps(open_roles), team_size, hiring_team, hiring_urgency, now))
            conn.commit()

    def get_inspection(self, company_name):
        """Fetch the latest inspection for a company."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute('''
                SELECT * FROM inspections WHERE company_name = ? ORDER BY timestamp DESC LIMIT 1
            ''', (company_name,)).fetchone()
            if row:
                result = dict(row)
                result['open_roles'] = json.loads(result['open_roles']) if result['open_roles'] else []
                return result
            return None

    def get_companies_by_score_range(self, min_score=80, max_score=100):
        """Fetch companies scoring in a range."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT DISTINCT c.* FROM companies c
                JOIN scores s ON c.name = s.company_name
                WHERE s.score >= ? AND s.score <= ?
                ORDER BY s.score DESC
            ''', (min_score, max_score)).fetchall()
            return [dict(row) for row in rows]
