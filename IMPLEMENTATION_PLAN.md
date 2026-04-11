# GigSaw: Implementation Plan

**Status:** Design Complete — Ready for Implementation  
**Last Updated:** April 11, 2026  
**Branch:** `claude/gigsaw-description-8deiw`

---

## Overview

GigSaw is a multi-agent career operations system for builders. The philosophy is documented in `CLAUDE.md`. This document specifies the implementation plan for **Tier 1 + Tier 2** (the five core modes that form the foundation).

The entire system is specification-first, code-second. CLAUDE.md defines what each mode should do. This document explains HOW to build it, with exact prompt structures, schemas, and error handling.

---

## The Five Core Modes (Phase 1a + 1b)

### 1. `/gigsaw arbitrage` — Intelligence Arbitrage Engine ⭐

**What it does:** Takes a job listing and reveals what the role is *becoming* in 12-18 months.

**Input:**
- Job URL (auto-fetched via Firecrawl or Claude web search)
- OR pasted job description

**Process:**
1. Parse job description (extract title, company, responsibilities, required skills, tools)
2. Identify AI vulnerabilities (which parts are vulnerable to augmentation/automation)
3. Map trajectory (what does this role look like in 12-18 months with AI maturity)
4. Identify the gap (what company doesn't see yet but will discover)
5. Position JJ in the gap (why his CIE framework + shipped work is perfect for future version)

**Output:** `data/arbitrage/[company]-[role].md`
```markdown
# Arbitrage Analysis: [Title] at [Company]

## ROLE AS WRITTEN
[What the JD says]

## ROLE AS BECOMING
[Specific trajectory with dated, tool-specific shifts]

## THE GAP
[What company doesn't know they need yet]

## JJ'S POSITION IN THE GAP
[Why he's already doing the future version]

## INTERVIEW REFRAME
[How to talk about this in interviews — not as written, but as becoming]

## PROOF BUILD SUGGESTION
[What to ship to demonstrate future competency]
```

**Quality Gates:**
- Specific AI vulnerabilities (not vague "AI will change everything")
- Honest about role transformation likelihood (some roles won't change much)
- Trajectory is plausible and grounded in shipped proof
- Tone is insightful, not arrogant ("I've noticed..." not "you don't understand your job")

**Key Design Decision:** Two-stage prompting
- Stage 1: Claude analyzes the 5 steps, generates analysis
- Stage 2: Claude formats output into structured report
- Both stages allow checkpoints where user can correct before proceeding

---

### 2. `/gigsaw propose` — Role Proposal Generator ⭐

**What it does:** Analyzes company's current job postings, finds what role is *missing*, writes it for them.

**Input:**
- Company name
- Their current job listings (from jobs.json or user pastes)

**Process:**

Three gap-detection strategies (use best match):

**Strategy A: Skill Overlap Analysis**
- Extract required skills from each posting
- Find skills appearing in 2+ roles but no unified position
- Example: Role A needs "copywriting + AI tools", Role B needs "design + AI tools" → missing "Creative AI Director" who unifies both

**Strategy B: Responsibility Fragmentation**
- Extract responsibilities from each posting
- Find clusters spanning multiple roles
- Example: Managing AI workflows (Role A), evaluating AI tools (Role B), briefing on AI (Role C) → missing unified "AI Creative Operations" role

**Strategy C: Seniority Ladder Gaps**
- Map reporting lines and seniority levels
- Identify missing levels or cross-functional coordinator roles

Then apply arbitrage lens: What does this missing role *become* as AI transforms it?

**Output:** `proposals/[company]-role-proposal.md` (1-2 pages, dense)
```markdown
# Role Proposal for [Company]

## THE PATTERN I NOTICED
[Specific gap from their postings]

## THE ROLE THAT'S MISSING
[Proposed title, function, reporting line]

## WHAT THIS ROLE PRODUCES
[Concrete 90-day outputs, not vague responsibilities]

## WHY THIS ROLE EXISTS NOW
[The AI capability shift that makes it necessary]

## WHY I'M WRITING THIS
[How JJ's work demonstrates he already does this]

## PROOF
[Links to shipped work + optional proof build]

## NEXT STEP
[Calendar link / specific ask]
```

**Quality Gates:**
- 60%+ skill overlap required across postings
- Proposed role must be distinct from existing listings
- Gap analysis is algorithmic, not generic ("you need better communication")
- JJ's shipped work directly connects to proposed role
- Confidence score is honest (low/medium/high)

**Key Design Decision:** **Not automated send** — HITL review only. User reviews the proposal before contacting company.

---

### 3. `/gigsaw setup` — Interview Agent v2

**What it does:** 6-round structured conversation → generates `profile.json`

**Rounds:**

1. **Builder Identity** (4-5 min)
   - Default stack, shipping speed, fastest ship example
   - Output: `build_capability` (default_stack, build_speed, fastest_ship)

2. **Shipped Work** (6-8 min)
   - Everything live, public, playable. For each: problem solved, URL, build time, what it proves
   - Output: `shipped_work[]` (title, url, problem_solved, stack, build_time, proves, status, tags)

3. **Problem-Solving Patterns** (5-7 min)
   - What problems gravitates toward, what reads first in JD, 48-hour build process
   - Output: `problem_patterns` (gravitates_toward, first_reads_in_jd, build_process)

4. **Traditional Profile** (5-6 min)
   - Work history, education, skills, awards
   - Output: `experience[]`, `education[]`, `skills`, `awards`

5. **Targets & Constraints** (5-7 min)
   - Target roles, companies, locations, remote preference, salary, dealbreakers
   - Output: `targets` and `constraints`

6. **Narrative & Positioning** (5-6 min)
   - 30-second origin story, unfair advantage, how to be perceived
   - Output: `narrative` (origin_story, unfair_advantage, positioning)

**Total Time:** 25-35 minutes, conversational tone (not a form)

**Quality Gates:**
- URLs required for shipped work (no URL = not shipped)
- Capabilities linked to proof (if you claim a skill, show shipped work)
- Vague answers: 1st clarification asks for specifics, 2nd probe diagnoses, then flag + move on
- No endless re-asking

**Output:** `profile.json`
```json
{
  "metadata": {
    "generated_at": "ISO timestamp",
    "interview_version": "2.0",
    "quality_score": 0.0-1.0
  },
  "build_capability": { ... },
  "shipped_work": [ ... ],
  "problem_patterns": { ... },
  "experience": [ ... ],
  "education": [ ... ],
  "targets": { ... },
  "constraints": { ... },
  "narrative": { ... }
}
```

**Key Design Decision:** Vagueness strategy
- 1st follow-up: "Give me specifics" (concrete example, numbers, URLs)
- 2nd follow-up: "Why?" (diagnostic — understand the underlying pattern)
- If still vague: Flag in `profile.notes.follow_up_needed` and move on
- Don't re-ask endlessly; respect user's time

---

### 4. `/gigsaw search` — Job Search Orchestration

**What it does:** Scrapes LinkedIn + Indeed using your target roles/locations.

**Input:** `profile.json` (extract `targets.roles`, `targets.locations`)

**Process:**
1. Read profile.json targets
2. Generate search queries (each role × each location)
3. Submit to Apify actors (sequential, 2-3s delay between submissions)
4. Poll results with exponential backoff
5. Deduplicate across sources
6. Write to jobs.json

**API Strategy:** HTTP REST (not SDK)
- Lighter weight, no dependency bloat
- Full control over retry logic
- Easier debugging

**Apify Actors:**
- `happitap/linkedin-job-scraper` (primary)
- `curious_coder/linkedin-jobs-scraper` (fallback, boolean search)

**Deduplication:** Composite key = `MD5(title + company + location)`
- Handles same job appearing on LinkedIn + Indeed
- Stores both URLs in `urls{}`
- Merges sources array if job found in multiple sources

**Output:** `data/jobs.json`
```json
{
  "version": "1.0",
  "fetched_at": "ISO timestamp",
  "total_jobs": 42,
  "jobs": [
    {
      "job_id": "string",
      "dedup_key": "hash",
      "title": "string",
      "company": "string",
      "location": "string",
      "remote": true,
      "salary_range": "string | null",
      "description": "string",
      "requirements": ["string"],
      "posted_date": "ISO date",
      "fetched_date": "ISO timestamp",
      "sources": ["linkedin", "indeed"],
      "urls": {
        "linkedin": "url",
        "indeed": "url"
      },
      "has_open_submission_signal": false,
      "target_match": {
        "role_match": "string",
        "location_match": "string"
      }
    }
  ]
}
```

**Rate Limiting:**
- Check Apify budget before running
- Sequential submission (2-3s delay)
- If rate-limited: wait 15min, retry up to 3x
- Partial success acceptable (10/12 queries = still valuable)

**Speed:** 2-3 minutes real-time

**Key Design Decision:** HTTP REST over SDK
- Simpler, no dependency bloat
- Better debugging (see full request/response)
- Full control over retry logic and rate limiting

---

### 5. `/gigsaw evaluate` — Job Evaluation Engine

**What it does:** Scores each job across 10 dimensions → assigns A-F grade.

**Input:** 
- Job URL, or
- Job ID from jobs.json, or
- Company + role name

**Process:**
1. Fetch/validate full job description
2. Extract structured fields
3. Evaluate 10 dimensions
4. Apply gate-pass logic
5. Calculate weighted GPA
6. Map to A-F grade
7. Generate narrative assessment

**The 10 Dimensions:**

| # | Dimension | Type | Weight | Notes |
|---|-----------|------|--------|-------|
| 1 | Role Match | Gate | — | Must be 6+/10 or grade floors to D+ |
| 2 | Skills Alignment | Gate | — | Must be 5+/10 or grade floors to D+ |
| 3 | Build-Fit | Weighted | 15% | Can JJ ship a proof build? How fast? |
| 4 | Arbitrage Potential | Weighted | 20% | How much will this role change with AI? |
| 5 | Company Stage & Culture | Weighted | 10% | Does company stage/mission match? |
| 6 | Compensation Alignment | Weighted | 8% | Does salary/equity fit targets? |
| 7 | Location/Remote Fit | Weighted | 8% | Does location match constraints? |
| 8 | Growth Trajectory | Weighted | 12% | Does role offer skill development? |
| 9 | Network Proximity | Weighted | 7% | Does JJ know anyone there? |
| 10 | Portfolio Alignment | Weighted | 8% | Does shipped work demonstrate fit? |

**Gate-Pass Logic:**
- If Role Match < 6: Grade = D+ (do not apply)
- If Skills Alignment < 5: Grade = D+ (do not apply)
- Otherwise: Calculate weighted GPA

**Weighted GPA Formula:**
```
Score = (Build-Fit × 0.15) + (Arbitrage × 0.20) + (Company × 0.10) + 
        (Compensation × 0.08) + (Location × 0.08) + (Growth × 0.12) + 
        (Network × 0.07) + (Portfolio × 0.08) + (Role Match × 0.10) + 
        (Skills × 0.02)
```

**Grade Mapping:**
- A: 9.0-10.0 (exceptional fit; apply with confidence)
- A-: 8.5-8.99 (excellent fit)
- B+: 8.0-8.49 (very good fit)
- B: 7.0-7.99 (good fit)
- B-: 6.5-6.99 (acceptable fit)
- C+: 6.0-6.49 (marginal fit)
- C: 5.0-5.99 (weak fit)
- Below C: Do not apply

**Quality Rule:** Strongly recommend against applying below B-.

**Output:** `data/evaluations/[company]-[role].md`
```markdown
# Job Evaluation: [Company] — [Role]

**Overall Grade: [A-F]**

## Summary
[1-2 sentence hook + recommendation]

## Dimension Scores
[Table with all 10 scores + brief reasoning]

## Deep Dives
[Detailed assessment per dimension]

## Next Steps
[Recommend /gigsaw arbitrage, /gigsaw build, etc.]
```

**Key Design Decisions:**
- Gate-pass logic prevents wasting time on fundamentally misaligned roles
- Arbitrage weight (20%) drives focus on role transformation (core differentiator)
- Build-Fit weight (15%) ensures proof builds are prioritized
- Network Proximity weight (7%) — warm path is nice-to-have, not make-or-break
- Transparent grading with no hidden formulas

---

## Implementation Roadmap

### Phase 1a: Core Foundation (4-5 days)
1. **`setup.md`** — Interview agent
   - Implement 6-round prompt structure with follow-up logic
   - Output profile.json schema
   - Test: Run full interview, verify profile quality_score ≥ 0.7

2. **`arbitrage.md`** — Role analysis engine
   - Implement two-stage prompting (analysis → output)
   - Implement 5-step process with checkpoints
   - Test: Analyze real job posting, verify 6 sections present

**Test End-to-End:** Interview → Arbitrage (profile.json feeds arbitrage context)

### Phase 1b: Job Pipeline (4-5 days)
3. **`search.md`** — Job search orchestration
   - Implement Apify HTTP REST client
   - Implement query generation from profile targets
   - Implement dedup logic
   - Test: Search 12 queries, return ≥10 unique jobs, verify dedup works

4. **`evaluate.md`** — Job scoring engine
   - Implement 10-dimension scoring
   - Implement gate-pass logic
   - Implement weighted GPA + A-F grade mapping
   - Test: Evaluate 10 jobs, verify grades range A-C, gate-pass blocks appropriate matches

**Test End-to-End:** Search → Evaluate (jobs ranked by grade)

### Phase 2: Differentiators + Application (2 weeks)
5. **`propose.md`** — Role proposal generator
6. **`build.md`** — Proof build proposer
7. **`remix.md`** — Application package generator
8. **`pdf.md`** — PDF generation
9. **`apply.md`** — ATS form filler

### Phase 3: Supporting Utilities (1 week)
10. **`who.md`** — Network check
11. **`scan.md`** — Career page monitor
12. **`track.md`** — Pipeline tracker
13. **`story.md`** — Story bank
14. **`wild.md`** — Unorthodox plays brainstormer

---

## Critical Implementation Notes

### Prompt Engineering (Arbitrage + Propose)

**Arbitrage Prompt Structure:**
- System: Establish 5-step process, include examples of "good" vs "bad" trajectories
- User: [Full job description]
- Model output: Analysis of each step with checkpoints

**Propose Prompt Structure:**
- Phase 1: Pattern recognition (skill overlap, fragmentation, seniority)
- Phase 2: Arbitrage analysis on the gap
- Phase 3: Proposal draft

### Required Data Files Before Testing

- `profile.json` — Minimal version: name, roles, locations, remote preference
- `data/connections.csv` — Placeholder with 2-3 entries for testing
- `config/portals.yml` — Populate with 3-5 target companies

### External Dependencies

```bash
# Must be set before running search.md
export APIFY_TOKEN=your_token_here

# Already installed
# - Playwright@^1.59.1
# - dotenv@^17.4.1
```

### File Structure to Create

```
modes/
  ├── arbitrage.md          ← Create
  ├── propose.md            ← Create
  ├── setup.md              ← Create
  ├── search.md             ← Create
  └── evaluate.md           ← Create

data/
  ├── apify-runs.log        ← Create (track run IDs)
  ├── jobs.json             ← Output
  ├── evaluations/          ← Output directory
  ├── arbitrage/            ← Output directory
  └── recon/                ← Output directory

proposals/                   ← Output directory
```

---

## Success Criteria

### Unit Tests (Per Mode)
- ✅ setup.md produces valid profile.json with quality_score ≥ 0.7
- ✅ search.md returns ≥5 unique jobs, dedup removes cross-posts correctly
- ✅ evaluate.md grades range A-F, gate-pass logic blocks appropriate matches
- ✅ arbitrage.md report has 6 sections, trajectory is plausible, proof linked
- ✅ propose.md identifies specific gaps, proposed role distinct from existing

### Integration Tests (End-to-End)
1. Interview generates profile.json ✓
2. Search generates jobs.json with 10+ listings ✓
3. Evaluate scores jobs A-F ✓
4. Arbitrage analyzes top-grade job, outputs 6-section report ✓
5. Propose identifies company gap, outputs 1-2 page proposal ✓

### Manual Testing
- Run `/gigsaw setup`, verify follow-up triggers, check profile.json completeness
- Paste real job, run `/gigsaw arbitrage`, verify tone is insightful not arrogant
- Pick company, run `/gigsaw propose`, verify gap is specific not generic

---

## Status

✅ **All five core modes fully designed and ready for implementation**

- Exact prompt structures documented
- Input/output schemas defined
- Error handling + edge cases specified
- Integration points mapped
- Quality gates established
- Testing strategies planned

**Next Steps:**
1. Implement Phase 1a (setup.md + arbitrage.md)
2. Test end-to-end
3. Implement Phase 1b (search.md + evaluate.md)
4. Proceed to Phase 2

---

**For full design details, see `/root/.claude/plans/merry-juggling-liskov.md` or the HTML version in this repository.**
