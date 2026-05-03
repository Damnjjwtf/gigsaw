"""SCOUT web dashboard — stdlib-only HTTP server over scout.db.

Terminal-aesthetic. Monospace. No JS framework. No emoji.
Read-only view into the pipeline.
"""

import json
import sqlite3
import html
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
from scout.config import Config
from scout.storage import ScoutStorage


CSS = """
* { box-sizing: border-box; }
body {
    font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
    background: #0a0a0a;
    color: #d4d4d4;
    margin: 0;
    padding: 24px;
    line-height: 1.5;
    font-size: 13px;
}
header {
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 12px;
    margin-bottom: 24px;
    display: flex;
    align-items: baseline;
    gap: 24px;
}
header h1 { margin: 0; font-size: 16px; font-weight: 600; color: #fff; letter-spacing: 0.04em; }
header .tag { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; }
header nav a {
    color: #888;
    text-decoration: none;
    margin-right: 16px;
    font-size: 12px;
}
header nav a:hover { color: #fff; }
header nav a.active { color: #4ade80; }
main { max-width: 1280px; margin: 0 auto; }
section { margin-bottom: 32px; }
h2 { font-size: 12px; text-transform: uppercase; color: #888; letter-spacing: 0.12em; margin: 0 0 12px 0; font-weight: 500; }
h3 { font-size: 14px; color: #fff; margin: 0 0 8px 0; font-weight: 600; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.stat {
    background: #141414;
    border: 1px solid #2a2a2a;
    padding: 12px 16px;
}
.stat .label { font-size: 10px; text-transform: uppercase; color: #666; letter-spacing: 0.1em; }
.stat .value { font-size: 22px; color: #fff; font-weight: 600; margin-top: 4px; }
.stat .sub { font-size: 11px; color: #666; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #1f1f1f; }
th { color: #888; font-weight: 500; text-transform: uppercase; font-size: 10px; letter-spacing: 0.1em; background: #0f0f0f; }
tr:hover td { background: #141414; }
a { color: #60a5fa; text-decoration: none; }
a:hover { text-decoration: underline; }
.score { display: inline-block; padding: 2px 8px; border-radius: 2px; font-weight: 600; font-size: 11px; }
.score.high { background: #14532d; color: #4ade80; }
.score.med { background: #422006; color: #fbbf24; }
.score.low { background: #1f1f1f; color: #888; }
.empty { color: #666; padding: 24px; text-align: center; border: 1px dashed #2a2a2a; }
pre { background: #141414; border: 1px solid #2a2a2a; padding: 16px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }
.muted { color: #666; }
.hist-bar { display: inline-block; height: 12px; background: #4ade80; vertical-align: middle; margin-right: 8px; }
.hist-row { display: flex; align-items: center; padding: 2px 0; font-size: 12px; }
.hist-label { width: 60px; color: #888; }
.hist-count { color: #fff; margin-left: 8px; }
.cmd-hint { background: #141414; border-left: 2px solid #4ade80; padding: 8px 12px; margin-top: 12px; font-size: 12px; color: #d4d4d4; }
"""


def score_class(score):
    if score is None:
        return 'low'
    if score >= 80:
        return 'high'
    if score >= 60:
        return 'med'
    return 'low'


def fmt_amount(amt):
    if not amt:
        return '-'
    if amt >= 1_000_000:
        return f"${amt / 1_000_000:.1f}M"
    if amt >= 1_000:
        return f"${amt / 1_000:.0f}K"
    return f"${amt}"


def fmt_date(s):
    if not s:
        return '-'
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except Exception:
        return s[:10] if len(s) > 10 else s


def page(title, body, active=''):
    nav_items = [
        ('/', 'dashboard'),
        ('/companies', 'companies'),
        ('/runs', 'runs'),
    ]
    nav = ''.join(
        f'<a href="{href}" class="{"active" if active == label else ""}">{label}</a>'
        for href, label in nav_items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SCOUT — {html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header>
    <h1>SCOUT</h1>
    <span class="tag">startup intelligence — {html.escape(title)}</span>
    <nav style="margin-left: auto;">{nav}</nav>
</header>
<main>{body}</main>
</body>
</html>"""


class WebQueries:
    """Read-only data access for dashboard views."""

    def __init__(self):
        self.db_path = Config.DB_PATH

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def stats(self):
        with self._conn() as conn:
            total = conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
            scored = conn.execute('SELECT COUNT(DISTINCT company_name) FROM scores').fetchone()[0]
            high = conn.execute('SELECT COUNT(DISTINCT company_name) FROM scores WHERE score >= 80').fetchone()[0]
            drafted = conn.execute('SELECT COUNT(DISTINCT company_name) FROM drafts').fetchone()[0]
            inspected = conn.execute('SELECT COUNT(DISTINCT company_name) FROM inspections').fetchone()[0]
            last_run = conn.execute('SELECT timestamp, source FROM runs ORDER BY timestamp DESC LIMIT 1').fetchone()
        return {
            'total': total,
            'scored': scored,
            'high': high,
            'drafted': drafted,
            'inspected': inspected,
            'last_run': dict(last_run) if last_run else None,
        }

    def score_distribution(self):
        buckets = {'80-100': 0, '60-79': 0, '40-59': 0, '0-39': 0}
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT company_name, MAX(score) as s FROM scores GROUP BY company_name'
            ).fetchall()
        for row in rows:
            s = row['s']
            if s is None:
                continue
            if s >= 80:
                buckets['80-100'] += 1
            elif s >= 60:
                buckets['60-79'] += 1
            elif s >= 40:
                buckets['40-59'] += 1
            else:
                buckets['0-39'] += 1
        return buckets

    def top_targets(self, limit=10):
        with self._conn() as conn:
            rows = conn.execute('''
                SELECT c.name, c.stage, c.amount_usd, c.source, c.announced_date,
                       MAX(s.score) as score
                FROM companies c
                LEFT JOIN scores s ON c.name = s.company_name
                GROUP BY c.name
                HAVING score IS NOT NULL
                ORDER BY score DESC
                LIMIT ?
            ''', (limit,)).fetchall()
        return [dict(r) for r in rows]

    def all_companies(self, sort='date'):
        order = 'c.announced_date DESC' if sort == 'date' else 'score DESC NULLS LAST'
        with self._conn() as conn:
            rows = conn.execute(f'''
                SELECT c.name, c.stage, c.amount_usd, c.source, c.announced_date,
                       c.location, MAX(s.score) as score
                FROM companies c
                LEFT JOIN scores s ON c.name = s.company_name
                GROUP BY c.name
                ORDER BY {order}
            ''').fetchall()
        return [dict(r) for r in rows]

    def recent_runs(self, limit=20):
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?', (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def company_detail(self, name):
        storage = ScoutStorage()
        company = storage.get_company(name)
        if not company:
            return None
        with self._conn() as conn:
            score_row = conn.execute(
                'SELECT * FROM scores WHERE company_name = ? ORDER BY timestamp DESC LIMIT 1',
                (name,),
            ).fetchone()
        return {
            'company': company,
            'score': dict(score_row) if score_row else None,
            'draft': storage.get_draft(name),
            'inspection': storage.get_inspection(name),
        }


def render_dashboard(q):
    s = q.stats()
    dist = q.score_distribution()
    top = q.top_targets(10)
    runs = q.recent_runs(5)

    last_run_html = (
        f"{html.escape(s['last_run']['source'])} · {fmt_date(s['last_run']['timestamp'])}"
        if s['last_run'] else '<span class="muted">never</span>'
    )

    stats_html = f"""
<section>
    <h2>Pipeline Status</h2>
    <div class="grid">
        <div class="stat"><div class="label">Companies</div><div class="value">{s['total']}</div><div class="sub">in database</div></div>
        <div class="stat"><div class="label">Scored</div><div class="value">{s['scored']}</div><div class="sub">{s['total'] - s['scored']} unscored</div></div>
        <div class="stat"><div class="label">High Value</div><div class="value">{s['high']}</div><div class="sub">score &ge; 80</div></div>
        <div class="stat"><div class="label">Drafted</div><div class="value">{s['drafted']}</div><div class="sub">cold outreach written</div></div>
        <div class="stat"><div class="label">Inspected</div><div class="value">{s['inspected']}</div><div class="sub">career pages checked</div></div>
        <div class="stat"><div class="label">Last Run</div><div class="value" style="font-size:14px;">{last_run_html}</div><div class="sub">most recent fetch</div></div>
    </div>
</section>
"""

    max_count = max(dist.values()) if any(dist.values()) else 1
    hist_html = ''.join(
        f'<div class="hist-row"><span class="hist-label">{label}</span>'
        f'<span class="hist-bar" style="width:{(count / max_count) * 280}px;"></span>'
        f'<span class="hist-count">{count}</span></div>'
        for label, count in dist.items()
    )

    top_rows = ''.join(
        f'<tr>'
        f'<td><a href="/company?name={html.escape(c["name"])}">{html.escape(c["name"])}</a></td>'
        f'<td><span class="score {score_class(c["score"])}">{c["score"] or "-"}</span></td>'
        f'<td>{html.escape(c.get("stage") or "-")}</td>'
        f'<td>{fmt_amount(c.get("amount_usd"))}</td>'
        f'<td class="muted">{html.escape(c.get("source") or "-")}</td>'
        f'</tr>'
        for c in top
    )
    if not top:
        top_rows = '<tr><td colspan="5" class="empty">No scored companies yet. Run <code>scout score</code>.</td></tr>'

    runs_rows = ''.join(
        f'<tr>'
        f'<td class="muted">{fmt_date(r["timestamp"])}</td>'
        f'<td>{html.escape(r["source"])}</td>'
        f'<td>{r["companies_found"]}</td>'
        f'<td>{r["companies_new"]}</td>'
        f'<td class="muted">{html.escape(r["status"] or "-")}</td>'
        f'</tr>'
        for r in runs
    )
    if not runs:
        runs_rows = '<tr><td colspan="5" class="empty">No runs yet. Run <code>scout feed</code>.</td></tr>'

    body = f"""
{stats_html}
<section>
    <h2>Score Distribution</h2>
    {hist_html}
</section>
<section>
    <h2>Top Targets</h2>
    <table>
        <thead><tr><th>Company</th><th>Score</th><th>Stage</th><th>Amount</th><th>Source</th></tr></thead>
        <tbody>{top_rows}</tbody>
    </table>
</section>
<section>
    <h2>Recent Runs</h2>
    <table>
        <thead><tr><th>When</th><th>Source</th><th>Found</th><th>New</th><th>Status</th></tr></thead>
        <tbody>{runs_rows}</tbody>
    </table>
</section>
<div class="cmd-hint">Next: run <code>python3 -m scout.cli arbitrage "[Company]"</code> on a top target to see what the role is becoming.</div>
"""
    return page('dashboard', body, active='dashboard')


def render_companies(q):
    rows = q.all_companies(sort='date')
    rows_html = ''.join(
        f'<tr>'
        f'<td><a href="/company?name={html.escape(c["name"])}">{html.escape(c["name"])}</a></td>'
        f'<td><span class="score {score_class(c["score"])}">{c["score"] or "-"}</span></td>'
        f'<td>{html.escape(c.get("stage") or "-")}</td>'
        f'<td>{fmt_amount(c.get("amount_usd"))}</td>'
        f'<td class="muted">{fmt_date(c.get("announced_date"))}</td>'
        f'<td class="muted">{html.escape(c.get("location") or "-")}</td>'
        f'<td class="muted">{html.escape(c.get("source") or "-")}</td>'
        f'</tr>'
        for c in rows
    )
    if not rows:
        rows_html = '<tr><td colspan="7" class="empty">No companies. Run <code>scout feed</code>.</td></tr>'
    body = f"""
<section>
    <h2>All Companies ({len(rows)})</h2>
    <table>
        <thead><tr><th>Name</th><th>Score</th><th>Stage</th><th>Amount</th><th>Announced</th><th>Location</th><th>Source</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
</section>
"""
    return page('companies', body, active='companies')


def render_runs(q):
    rows = q.recent_runs(100)
    rows_html = ''.join(
        f'<tr>'
        f'<td class="muted">{fmt_date(r["timestamp"])}</td>'
        f'<td>{html.escape(r["source"])}</td>'
        f'<td>{r["companies_found"]}</td>'
        f'<td>{r["companies_new"]}</td>'
        f'<td class="muted">{html.escape(r["status"] or "-")}</td>'
        f'</tr>'
        for r in rows
    )
    if not rows:
        rows_html = '<tr><td colspan="5" class="empty">No runs.</td></tr>'
    body = f"""
<section>
    <h2>Pipeline Runs ({len(rows)})</h2>
    <table>
        <thead><tr><th>When</th><th>Source</th><th>Found</th><th>New</th><th>Status</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
</section>
"""
    return page('runs', body, active='runs')


def render_company(q, name):
    detail = q.company_detail(name)
    if not detail:
        return page('not found', f'<div class="empty">Company "{html.escape(name)}" not in database.</div>'), 404
    c = detail['company']
    s = detail['score']
    d = detail['draft']
    insp = detail['inspection']

    score_block = (
        f'<section><h2>Score</h2>'
        f'<div class="stat"><div class="label">Fit Score</div>'
        f'<div class="value"><span class="score {score_class(s["score"])}">{s["score"]}</span></div>'
        f'<div class="sub muted">{fmt_date(s["timestamp"])}</div></div>'
        f'<pre>{html.escape(s.get("rationale") or "")}</pre></section>'
        if s else
        '<section><h2>Score</h2><div class="empty">Not scored. <code>scout score</code></div></section>'
    )

    draft_block = (
        f'<section><h2>Cold Outreach Draft</h2>'
        f'<div class="muted" style="margin-bottom:8px;">{fmt_date(d["timestamp"])} · tone: {html.escape(d.get("tone") or "warm")}</div>'
        f'<pre><strong>Subject:</strong> {html.escape(d.get("subject") or "")}\n\n{html.escape(d.get("body") or "")}</pre></section>'
        if d else
        '<section><h2>Cold Outreach Draft</h2><div class="empty">No draft. <code>scout draft "' + html.escape(name) + '"</code></div></section>'
    )

    if insp:
        roles = insp.get('open_roles') or []
        roles_html = ''.join(f'<li>{html.escape(r)}</li>' for r in roles) or '<li class="muted">none detected</li>'
        insp_block = (
            f'<section><h2>Career Page Inspection</h2>'
            f'<div class="grid">'
            f'<div class="stat"><div class="label">Open Roles</div><div class="value">{len(roles)}</div></div>'
            f'<div class="stat"><div class="label">Team Size</div><div class="value">{insp.get("team_size") or "-"}</div></div>'
            f'<div class="stat"><div class="label">Hiring Urgency</div><div class="value" style="font-size:14px;">{html.escape(insp.get("hiring_urgency") or "-")}</div></div>'
            f'</div>'
            f'<h3 style="margin-top:16px;">Detected Roles</h3>'
            f'<ul>{roles_html}</ul></section>'
        )
    else:
        insp_block = '<section><h2>Career Page Inspection</h2><div class="empty">Not inspected. <code>scout inspect "' + html.escape(name) + '"</code></div></section>'

    investors_html = ''
    try:
        investors = json.loads(c.get('investors') or '[]')
        if investors:
            investors_html = ', '.join(html.escape(i) for i in investors)
    except Exception:
        pass

    website_link = (
        f'<a href="{html.escape(c["website"])}" target="_blank" rel="noopener">{html.escape(c["website"])}</a>'
        if c.get('website') else '<span class="muted">-</span>'
    )

    body = f"""
<section>
    <h2>Company</h2>
    <h3>{html.escape(c['name'])}</h3>
    <p class="muted">{html.escape(c.get('description') or '')}</p>
    <div class="grid">
        <div class="stat"><div class="label">Stage</div><div class="value" style="font-size:14px;">{html.escape(c.get('stage') or '-')}</div></div>
        <div class="stat"><div class="label">Amount</div><div class="value" style="font-size:14px;">{fmt_amount(c.get('amount_usd'))}</div></div>
        <div class="stat"><div class="label">Announced</div><div class="value" style="font-size:14px;">{fmt_date(c.get('announced_date'))}</div></div>
        <div class="stat"><div class="label">Location</div><div class="value" style="font-size:14px;">{html.escape(c.get('location') or '-')}</div></div>
        <div class="stat"><div class="label">Source</div><div class="value" style="font-size:14px;">{html.escape(c.get('source') or '-')}</div></div>
        <div class="stat"><div class="label">Headcount</div><div class="value" style="font-size:14px;">{c.get('headcount') or '-'}</div></div>
    </div>
    <div style="margin-top:12px;">
        <strong class="muted">Website:</strong> {website_link}<br>
        <strong class="muted">Investors:</strong> {investors_html or '<span class="muted">-</span>'}
    </div>
</section>
{score_block}
{insp_block}
{draft_block}
<div class="cmd-hint">
    Run on this target:
    <code>scout arbitrage "{html.escape(name)}"</code> ·
    <code>scout propose "{html.escape(name)}"</code> ·
    <code>scout recon "{html.escape(name)}"</code> ·
    <code>scout who "{html.escape(name)}"</code>
</div>
"""
    return page(c['name'], body, active='companies'), 200


class ScoutHandler(BaseHTTPRequestHandler):
    queries = WebQueries()

    def log_message(self, format, *args):
        # Quiet by default; one line per request to stderr
        import sys
        sys.stderr.write(f"[scout-web] {self.address_string()} - {format % args}\n")

    def _send(self, status, body, content_type='text/html; charset=utf-8'):
        body_bytes = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body_bytes)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        try:
            if path == '/' or path == '/dashboard':
                self._send(200, render_dashboard(self.queries))
            elif path == '/companies':
                self._send(200, render_companies(self.queries))
            elif path == '/runs':
                self._send(200, render_runs(self.queries))
            elif path == '/company':
                name = (params.get('name') or [''])[0]
                if not name:
                    self._send(400, page('error', '<div class="empty">Missing ?name=</div>'))
                    return
                content, status = render_company(self.queries, name)
                self._send(status, content)
            elif path == '/api/companies':
                rows = self.queries.all_companies()
                self._send(200, json.dumps(rows, default=str), 'application/json')
            elif path == '/api/runs':
                rows = self.queries.recent_runs(100)
                self._send(200, json.dumps(rows, default=str), 'application/json')
            elif path == '/api/stats':
                self._send(200, json.dumps(self.queries.stats(), default=str), 'application/json')
            elif path == '/healthz':
                self._send(200, 'ok\n', 'text/plain; charset=utf-8')
            else:
                self._send(404, page('not found', '<div class="empty">404 — no such route.</div>'))
        except Exception as e:
            self._send(500, page('error', f'<div class="empty">500: {html.escape(str(e))}</div>'))


def serve(host='127.0.0.1', port=8000):
    """Start the SCOUT web dashboard."""
    # Ensure DB exists by touching storage
    ScoutStorage()
    server = ThreadingHTTPServer((host, port), ScoutHandler)
    print(f"SCOUT web dashboard")
    print(f"  Listening: http://{host}:{port}")
    print(f"  DB:        {Config.DB_PATH}")
    print(f"  Routes:    /  /companies  /runs  /company?name=X")
    print(f"  API:       /api/companies  /api/runs  /api/stats")
    print(f"  Stop:      Ctrl-C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.server_close()
