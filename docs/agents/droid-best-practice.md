# Droid Best Practice Guide

> This guide offers Droid-specific tips. For canonical repo rules and data contracts,
> **defer to `AGENTS.md` (root)** and the **Single Source of Truth `./data_model.md`**.

## Scope & Priority

This is a **companion guide** for Factory Droid workflows. Where guidance conflicts:
1. **`./data_model.md`** (root) — Single Source of Truth for schemas, services, UI contracts
2. **`AGENTS.md`** (root) — Canonical project playbook (tool-agnostic)
3. This guide — Vendor-specific tips and workflows

## Stack Defaults

**Primary Stack:**
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic
- **Database:** PostgreSQL 16 (compatible with 14+)
- **Auth/Crypto:** JWT (short-lived + revocation), Fernet (sensitive fields), Argon2 (passwords)
- **Validation:** Pydantic v2

**Optional (if `package.json` exists):**
- **Node.js** tooling for type generation, UI components
- Examples shown for completeness; apply only if relevant

## Core Workflow: Plan → Implement → Review

### 1. Planning Phase
**Before any code changes:**

```bash
# Droid reads AGENTS.md and ./data_model.md automatically via .droid.yaml
# Your plan should include:
```

- **Files to touch** (aim 3–6 files max per iteration)
- **Tests to add/update** (co-tag test files)
- **Risks & rollback plan** (especially for migrations)
- **Data model alignment** (cite entities/relations from ./data_model.md)

**Constraints:**
- Target **30–75 LOC** of change per iteration
- Prefer **additive** migrations (avoid destructive unless planned)
- If a file exceeds **~500 LOC**, propose extraction/splitting

### 2. Implementation Phase
**Small, testable diffs:**

- Return only **minimal patched hunks** (not entire files)
- Add inline comments only where necessary (no redundant docs)
- Create Alembic migrations for schema changes:
  ```bash
  alembic revision --autogenerate -m "add index on test_sessions.created_at"
  ```
- Stage related changes together (model + schema + test)

### 3. Review Phase
**Before finalizing:**

- **Security Gate** (see below)
- **Tests pass:** `pytest -q`
- **Migrations apply:** `alembic upgrade head`
- **Linting:** `ruff check . || true` (best-effort)
- **Summarize:** Files changed, LOC delta, test coverage, rollback steps

## Security Gate (Must Pass)

Every change must satisfy:

1. **Input Validation**
   - Use Pydantic v2 models for all request/response bodies
   - Parameterized queries only (SQLAlchemy 2.0 syntax)

2. **Authorization**
   - Check `current_user` permissions on protected endpoints
   - Never trust client-provided IDs without authZ verification

3. **Secrets Management**
   - All secrets in `.env` or secret manager
   - Never hardcode keys, tokens, or connection strings

4. **Web Security**
   - Set headers: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
   - Configure CORS with explicit origins (no `*` in production)
   - CSRF protection for state-changing operations

5. **Cryptography**
   - **JWT:** Short-lived tokens (≤15 min) + revocation list (RTL)
   - **Fernet:** Encrypt PII/sensitive fields at rest
   - **Argon2:** Hash passwords (never bcrypt or plain SHA)

6. **Database Security**
   - JSONB columns → **GIN** indexes (per ./data_model.md)
   - FK constraints, unique constraints, partial indexes for soft-deletes
   - Temporal indexes on `created_at`/`updated_at`

7. **Error Handling**
   - Structured errors (no raw stack traces to clients)
   - Never leak secrets, connection strings, or internal paths

## Single Source of Truth Usage

For **any data-impacting change**:

1. **Reference `./data_model.md`**
   - Identify affected entities/relations in the ERD
   - Note required indexes (JSONB/GIN, FK, unique, temporal)

2. **Prefer Additive Migrations**
   - Add columns with defaults
   - Create indexes concurrently (if supported)
   - Avoid `DROP COLUMN` or `ALTER COLUMN TYPE` without backfill plan

3. **Cite ERD Sections**
   - Example: "Modifies `TestSession` (§3.2) to add `compliance_checklist` JSONB field with GIN index"

4. **Update SoT After Major Changes**
   - After merging structural changes, regenerate/update `./data_model.md` using your model-generation workflow

## CI & PR Checklist

**CI Stage Order:**
1. Install → Lint → Typecheck → Unit Tests → Integration Tests
2. Security Scan → Build → Preview Deploy (if applicable)

**PR Checklist** (link to AGENTS.md):
- [ ] Small, reviewable diff; tests added/updated
- [ ] Change references `./data_model.md` for data-touching work
- [ ] Security Gate passed (validation, authZ, JWT/Fernet/Argon2, headers, indexes)
- [ ] DB indexes/constraints align with SoT (JSONB/GIN, FK, unique, temporal)
- [ ] Rollback plan documented (if migrations or destructive changes)

**Blocking Conditions:**
- Failing tests
- High/critical security vulnerabilities
- Missing MPKF-Ref or ticket reference (per repo conventions)

## Python-Specific Tips

### Environment Setup
```bash
# Create venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
# or with poetry:
poetry install
```

### Running the App
```bash
# Development server
uvicorn app.main:app --reload

# With custom port
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Testing
```bash
# Run all tests
pytest -q

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific test file
pytest tests/unit/test_defects.py -v
```

### Migrations
```bash
# Auto-generate migration
alembic revision --autogenerate -m "add defect severity enum"

# Apply migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1

# Show current version
alembic current
```

### Linting/Formatting
```bash
# Ruff (if available)
ruff check .
ruff format .

# Black + isort (fallback)
black .
isort .
```

## Node.js Tips (Optional)

> Only apply if `package.json` exists in your repo.

### Environment Setup
```bash
npm ci  # Clean install from package-lock.json
```

### Type Generation
```bash
# Generate TypeScript types from JSON schemas
npm run generate:types
```

### Testing
```bash
npm test
npm run test:watch
```

### Linting
```bash
npm run lint
npm run typecheck
```

## Commit Conventions

**Follow MPKF format** (per repo conventions):
```
<type>(<scope>): <subject> [FM-ENH-XXX]

<body with details>

MPKF-Ref: TDD-v4.0-Section-X,v3.1

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>
```

**Types:** `feat`, `fix`, `docs`, `chore`, `test`, `refactor`, `perf`, `ci`, `build`

## Common Droid Workflows

### 1. Add a New Endpoint
```markdown
**Plan:**
- File: `src/app/routes/buildings.py` (+20 LOC)
- File: `src/app/schemas/building.py` (import existing)
- File: `tests/integration/test_buildings_api.py` (+15 LOC)
- Risk: None (read-only endpoint)
- SoT: Uses `Building` entity (§2.1)

**Implement:**
1. Add GET endpoint with pagination
2. Add integration test with auth
3. Run tests + ruff

**Review:**
- Security Gate: ✅ (authZ check, Pydantic validation)
- Tests: ✅ (1 integration test added)
- SoT: ✅ (no schema change)
```

### 2. Add Database Index
```markdown
**Plan:**
- File: `alembic/versions/xxx_add_test_sessions_idx.py` (new migration, +15 LOC)
- Risk: Index creation may lock table briefly
- SoT: `TestSession.created_at` index (§3.2 recommends temporal indexes)

**Implement:**
1. Create migration: `alembic revision -m "add idx_test_sessions_created_at"`
2. Add `op.create_index('idx_test_sessions_created_at', 'test_sessions', ['created_at'])`
3. Add downgrade: `op.drop_index('idx_test_sessions_created_at')`

**Review:**
- Security Gate: ✅ (no code change)
- Tests: ✅ (migration applies cleanly)
- SoT: ✅ (aligns with temporal index requirement)
```

### 3. Add JSONB Field with GIN Index
```markdown
**Plan:**
- File: `alembic/versions/xxx_add_compliance_checklist.py` (+25 LOC)
- File: `src/app/models/test_session.py` (+5 LOC)
- File: `tests/unit/test_test_session_model.py` (+10 LOC)
- Risk: Migration adds nullable column (safe)
- SoT: `TestSession` (§3.2) extended with JSONB field

**Implement:**
1. Add migration with `op.add_column('test_sessions', sa.Column('compliance_checklist', JSONB))`
2. Add GIN index: `op.execute('CREATE INDEX idx_test_sessions_checklist_gin ON test_sessions USING gin (compliance_checklist jsonb_path_ops)')`
3. Update model with `compliance_checklist: Mapped[Optional[dict]]`
4. Add unit test verifying JSONB serialization

**Review:**
- Security Gate: ✅ (nullable column, GIN index per SoT)
- Tests: ✅ (unit test covers JSONB ops)
- SoT: ✅ (follows §3.2 JSONB + GIN pattern)
```

## Troubleshooting

### Alembic Conflicts
```bash
# Check current state
alembic current
alembic history

# Merge heads (if multiple branches)
alembic merge -m "merge migration branches" head1 head2
```

### Import Errors
```bash
# Ensure PYTHONPATH includes src
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or use pytest.ini / pyproject.toml
```

### Test Database Issues
```bash
# Reset test DB
dropdb test_db
createdb test_db
alembic upgrade head
```

## Anti-Patterns to Avoid

❌ **Don't:**
- Commit without reading `./data_model.md` for data changes
- Make >75 LOC changes in one iteration
- Skip tests ("will add later")
- Use bare `except:` (use `except Exception as e:`)
- Hardcode secrets in code or logs
- Use `SELECT *` or raw SQL strings
- Skip Security Gate review

✅ **Do:**
- Read AGENTS.md + ./data_model.md first (automated via `.droid.yaml`)
- Break large changes into 30–75 LOC chunks
- Co-tag test files when planning
- Use Pydantic models + parameterized queries
- Reference ERD sections in commit messages
- Run full test suite before PR

## Resources

- **Canonical Playbook:** `AGENTS.md` (root)
- **Single Source of Truth:** `./data_model.md` (root)
- **Droid Config:** `.droid.yaml` (enforces SoT reading)
- **CI Workflow:** `.github/workflows/ci.yml` or `ci-sot-aligned.yml`
- **PR Template:** `.github/PULL_REQUEST_TEMPLATE.md`

---

**Last Updated:** 2025-10-27  
**Maintained by:** FireMode Compliance Platform Team  
**Feedback:** Open an issue or PR with improvements
