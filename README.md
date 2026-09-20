# Gigsaw

**A ship-first career operations system for finding problems worth solving before applying for the job.**

Most job-search tools optimize resumes, keywords, and application volume. Gigsaw takes a different approach: research the company, identify a real operating problem, build a small proof that addresses it, then use the application to explain the work.

The system is built around one idea:

> **The system is the resume.**

## What it does

Gigsaw combines research, job evaluation, company reconnaissance, proof-build planning, application tailoring, and pipeline tracking into one repeatable workflow.

```text
Find role
  ↓
Understand the company
  ↓
Identify the real problem behind the listing
  ↓
Model how the role is changing
  ↓
Design a small proof build
  ↓
Ship it
  ↓
Use the application to explain the evidence
  ↓
Track, learn, improve
```

## Core ideas

### Ship First
Instead of treating a resume as the primary artifact, Gigsaw prioritizes working evidence: a prototype, audit, research system, workflow, or other small build tied to the target company's problem.

### SIBA: Solve Issues Before Applying
Find a concrete problem. Build something useful around it. Apply with evidence rather than promises.

### Intelligence Arbitrage
Job descriptions describe what a company already knows it needs. Gigsaw also asks what the role is becoming as AI changes the work, then looks for the gap between the posted role and the emerging one.

## Modes

| Command | Purpose |
| --- | --- |
| `/gigsaw search` | Find relevant roles |
| `/gigsaw scan` | Watch target-company career pages |
| `/gigsaw evaluate [url]` | Evaluate a role across defined criteria |
| `/gigsaw arbitrage [url]` | Analyze how the role is changing |
| `/gigsaw propose [company]` | Draft the role the company may need next |
| `/gigsaw recon [company]` | Research the company before applying |
| `/gigsaw build [url]` | Design a proof build for the role |
| `/gigsaw who [company]` | Look for warm paths and relevant people |
| `/gigsaw remix [url]` | Tailor application materials around the proof |
| `/gigsaw track` | Track applications, follow-ups, and deadlines |
| `/gigsaw story` | Maintain an interview story bank |

## What this repo demonstrates

Gigsaw is also a portfolio artifact. It shows how I approach ambiguous problems:

- turn a fuzzy goal into a system
- combine qualitative research with structured evaluation
- use AI agents as coordinated workflow components rather than isolated chat prompts
- keep human review at consequential steps
- connect research to something shipped
- treat the output of a system as evidence, not decoration

## Structure

```text
CLAUDE.md       master operating instructions
config/         system configuration
modes/          task-specific operating modes
data/           structured working data
stories/        interview and proof stories
templates/      reusable output templates
gigsaw.html     lightweight interface
```

The current implementation uses Claude Code for orchestration, plus Node tooling and Playwright where browser automation is useful.

## Status

Gigsaw is an active working system, not a finished SaaS product. The useful question is not whether every feature is polished. It is whether the system helps turn a job opportunity into a sharper hypothesis, a stronger proof build, and a better application.

## Why I built it

I work across copywriting, product thinking, AI workflows, research, and creative technology. Traditional job-search tools flatten that mix into keywords.

Gigsaw does the opposite. It turns the way I work into the application itself.
