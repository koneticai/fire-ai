# Canonical Paths & Monorepo Layout

**Purpose:** Document canonical directory paths for CI/CD, development tools, and deployment scripts.  
**Last Updated:** 2025-10-14  
**Owner:** Platform Team

---

## Overview

Fire-AI uses a **monorepo layout** with multiple service types organized by language and deployment strategy. This document defines canonical paths to ensure consistency across:

- GitHub Actions workflows
- Local development scripts
- Deployment automation
- Replit synchronization

---

## Canonical Paths

### Python Services

**Location:** `services/api/`

```
services/api/
├── pyproject.toml          # Poetry dependency management
├── poetry.lock             # Locked dependencies
├── src/
│   └── app/               # Main application code
│       ├── main.py
│       ├── routers/
│       ├── models/
│       └── schemas/
└── tests/                 # Python test suite
    ├── test_*.py
    └── integration/
```

**CI Working Directory:** `services/api`

**Why this path?**
- Isolated dependency management per service
- Supports future microservice expansion (e.g., `services/auth/`, `services/classifier/`)
- Aligns with monorepo best practices

**Tools using this path:**
- `.github/workflows/ci.yml` → `lint-python` and `test-python` jobs
- `scripts/full-check.sh` → Python validation section
- Local Poetry commands: `cd services/api && poetry install`

---

### Go Services (Optional)

**Primary Location:** `src/go_service/`  
**Alternative Location:** `services/api/src/go_service/` (legacy)

```
src/go_service/
├── main.go                # Go service entrypoint
├── go.mod                 # Go module definition
├── go.sum                 # Go dependency checksums
└── *.go                   # Additional Go source files
```

**CI Detection Logic:** (See `.github/workflows/ci.yml` → `build-go` job)

```yaml
- name: Detect Go service path
  run: |
    if [ -d "src/go_service" ] && [ -f "src/go_service/main.go" ]; then
      echo "path=src/go_service"
    elif [ -d "services/api/src/go_service" ] && [ -f "services/api/src/go_service/main.go" ]; then
      echo "path=services/api/src/go_service"
    else
      echo "path="  # Not found - skip Go steps
    fi
```

**Why is Go optional?**

1. **Incremental Migration:** The Go service is being refactored from a legacy location to a canonical path.
2. **Development Flexibility:** Some development branches may not include Go components yet.
3. **Graceful Degradation:** CI should not fail if Go service is absent; Python services are the core functionality.

**When Go is absent:**
- GitHub Actions will **skip** Go build/test steps with a clear message
- CI pipeline remains **green** (all Python checks pass)
- No deployment blockers

**Migration Plan:**
- Current state: Go service exists at `src/go_service/` (canonical)
- Future: Consolidate all Go services under `services/` (e.g., `services/classifier-go/`)
- See: [ADR-0001: Repository Foundation](../adr/0001-repo-foundation.md)

---

### Frontend/UI

**Location:** `packages/ui/`

```
packages/ui/
├── package.json           # npm/yarn dependencies
├── src/
│   ├── atoms/            # Atomic design - atoms
│   ├── molecules/        # Atomic design - molecules
│   ├── organisms/        # Atomic design - organisms
│   └── stories/          # Storybook stories
├── storybook-static/     # Built Storybook artifacts
└── tsconfig.json         # TypeScript configuration
```

**CI Status:** Not yet integrated (Phase 5+)

**Why this path?**
- Follows **atomic design** principles (atoms → molecules → organisms)
- Isolates frontend dependencies from backend services
- Enables independent versioning and deployment

---

## Monorepo Layout Rationale

### Current Structure

```
fire-ai/
├── services/              # Backend services (Python)
│   └── api/              # Main FastAPI service
├── src/                  # Shared utilities & Go services
│   ├── app/              # Legacy Python app (being phased out)
│   └── go_service/       # Go services (transitional location)
├── packages/             # Frontend packages (TypeScript/React)
│   └── ui/               # Component library
├── tests/                # Integration & contract tests
├── scripts/              # DevOps automation
└── docs/                 # Technical documentation
```

### Design Principles

1. **Service Isolation:** Each service (`services/api/`) has its own `pyproject.toml` and dependencies.
2. **Language Separation:** Python (services/), Go (src/), TypeScript (packages/).
3. **Shared Resources:** Cross-cutting concerns (tests/, docs/, scripts/) at root level.
4. **CI Compatibility:** GitHub Actions can run jobs with `working-directory` targeting specific services.

### Future Evolution

**Phase 6+ Roadmap:**
- Consolidate `src/app/` → `services/api/src/app/` (eliminate duplicate Python paths)
- Move `src/go_service/` → `services/classifier-go/` (align Go with service pattern)
- Add `services/auth/` for dedicated authentication service
- Introduce `packages/web/` for Next.js frontend

---

## CI/CD Integration

### GitHub Actions Path Logic

**Python Jobs:** Always run (services exist)
```yaml
defaults:
  run:
    working-directory: services/api
```

**Go Jobs:** Conditionally run (optional)
```yaml
- name: Detect Go service path
  id: gosvc
  run: |
    if [ -d "src/go_service" ] && [ -f "src/go_service/main.go" ]; then
      echo "path=src/go_service"
    else
      echo "path="  # Skip Go steps
    fi

- name: Build Go service (if present)
  if: steps.gosvc.outputs.path != ''
  run: cd ${{ steps.gosvc.outputs.path }} && go build
```

**Security Scans:** Target Python dependencies
```bash
cd services/api
poetry export | safety check --stdin
```

---

## Local Development Commands

### Python

```bash
# Install dependencies
cd services/api
poetry install

# Run tests
poetry run pytest

# Lint
poetry run pylint src/app
```

### Go (if present)

```bash
# Build
cd src/go_service
go build -v ./...

# Test
go test -v ./...
```

### TypeScript/UI

```bash
# Install dependencies
cd packages/ui
npm install

# Run Storybook
npm run storybook
```

---

## Troubleshooting

### CI Fails with "services/api not found"

**Cause:** Working directory mismatch in workflow.  
**Solution:** Verify `.github/workflows/ci.yml` uses `working-directory: services/api`.

### Go build fails in CI

**Cause:** Go service moved or deleted.  
**Solution:** CI will automatically skip if `main.go` not found. Check `build-go` job output for detection log.

### Python imports fail locally

**Cause:** Poetry environment not activated.  
**Solution:** Run `cd services/api && poetry shell` before running Python commands.

---

## Related Documentation

- [ADR-0001: Repository Foundation](../adr/0001-repo-foundation.md) - Monorepo design decisions
- [Replit Sync Runbook](../runbooks/replit-sync.md) - Remote sync strategies
- [GitHub Actions Workflow](../../.github/workflows/ci.yml) - Full CI pipeline

---

## Summary

**Key Takeaway:** Use `services/api/` for Python, `src/go_service/` for Go (optional), and `packages/ui/` for frontend.

**CI Philosophy:** Python services are mandatory; Go and UI are optional and gracefully skipped if absent.

**Monorepo Benefits:** Isolated dependencies, language separation, and shared infrastructure.

