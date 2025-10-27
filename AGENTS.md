# AGENTS.md — Project Playbook for All Code Agents (Droid, Cursor, etc.)

This file is the **canonical project playbook**. It defers to **./data_model.md** as the Single Source of Truth (SoT) for schemas, services, and UI data.

> **SoT Path:** `./data_model.md` (root — do not move without updating this reference)

## 0) Goals & Guardrails
- Ship high-quality changes with **small, reviewable diffs** and strong security.
- Non-negotiables: Security gate passes; tests exist; every data-touching change **references `./data_model.md`**.

## 1) Session Rules (Plan → Implement small diffs → Review)
1. Plan: short plan (files, tests, risks) referencing `./data_model.md` where relevant.
2. Implement: **30–75 LOC per iteration**; prefer additive migrations/code.
3. Review: summarize diff, tests, rollback; confirm alignment with `./data_model.md`.

## 2) Repro: Build/Test/Run (Python primary; Node optional)
### Python (FastAPI + SQLAlchemy + Alembic)
- `python -m venv .venv && source .venv/bin/activate` (Win: `.venv\Scripts\activate`)
- `pip install -r requirements.txt` (or `uv pip sync`)
- `ruff check . && ruff format .` or `black . && isort .` (if present)
- `uvicorn app.main:app --reload`
- `pytest -q`
- `alembic upgrade head`

### Node (only if \`package.json\` exists)
- `npm ci` · `npm run typecheck && npm run lint` · `npm test`

## 3) Security Gate (must pass)
- Validation (FastAPI + Pydantic v2); parameterized queries (SQLAlchemy 2.0)
- AuthZ checks on protected paths; secrets only in env/secret manager
- Web security headers/CSP/CORS/CSRF as needed
- Crypto: **JWT** (short-lived + revocation), **Fernet** (sensitive fields), **Argon2** (passwords)
- DB: JSONB + **GIN**; FK/unique/temporal indexes per SoT
- Errors: structured; no secret/stack leakage

## 4) VCS & Checkpoints
- Commit after stable steps with concise rationale; prefer **small PRs**
- Keep `/architecture.md` updated with decisions

## 5) Mandatory — Single Source of Truth (Data Model)
- SoT file: `./data_model.md` (root)
- For any data-impacting task, reference SoT; prefer **additive** migrations
- After major changes, refresh SoT with your model-generation workflow

**Cleanup Prompt (post-SoT):**

```
Reference the file data_model.md. Analyze the existing codebase for duplications, inefficient patterns, unused files, and misalignments with the data model. Suggest targeted cleanups and refactors without altering core functionality. Provide a step-by-step plan, including files to modify or delete.
```

## 6) PR Checklist
- [ ] Small, reviewable diff; tests added/updated  
- [ ] Referenced `./data_model.md` for any data-touching change  
- [ ] Security Gate passed (validation, authZ, JWT/Fernet/Argon2, CSP/CORS/CSRF, secrets)  
- [ ] DB indexes/constraints align with SoT (JSONB/GIN/FK/unique/temporal)  
- [ ] Rollback plan considered (if needed)

## 7) Vendor Guides
- **Droid companion guide:** [/docs/agents/droid-best-practice.md](/docs/agents/droid-best-practice.md) — Factory Droid workflows, tips, and troubleshooting
