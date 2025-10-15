# Atomic Repair Summary - Replit & CI Hardening

**Date:** 2025-10-14  
**Orchestrator:** GPT-5 Enterprise Implementation  
**Status:** ✅ COMPLETE

---

## Objectives

✅ **A)** Add/validate Replit git remote OR document GitHub→Replit sync  
✅ **B)** Fix CI jobs trying to cd into missing Go path: `services/api/src/go_service`  
✅ **C)** Harden CI so missing directories fail gracefully with clear hints

---

## Changes Made

### 1. Replit Sync Documentation
📄 **New File:** `docs/runbooks/replit-sync.md`

Comprehensive runbook documenting TWO sync strategies:
- **Strategy 1 (Recommended):** GitHub Auto-Sync via Replit UI
- **Strategy 2:** Direct Push via `replit` git remote

Includes:
- Setup instructions for both strategies
- Push/pull workflow examples
- Bi-directional sync patterns
- Troubleshooting guide
- Git alias suggestions

### 2. Replit Remote Setup Script
📄 **New File:** `scripts/setup-replit-remote.sh` (executable)

Interactive script to configure Replit git remote:
```bash
./scripts/setup-replit-remote.sh [username] [token] [project]
```

Features:
- Interactive or command-line mode
- Checks for existing remote
- Validates required fields
- Masks token in output
- Shows usage examples

### 3. CI Pipeline Hardening
📝 **Modified:** `.github/workflows/ci.yml`

**Before:**
```yaml
- name: Build Go service
  run: |
    cd services/api/src/go_service  # ❌ Fails if path missing
    go build -v ./... || true
```

**After:**
```yaml
- name: Detect Go service path
  id: gosvc
  run: |
    if [ -d "src/go_service" ] && [ -f "src/go_service/main.go" ]; then
      echo "path=src/go_service" >> $GITHUB_OUTPUT
      echo "✓ Found Go service at src/go_service"
    elif [ -d "services/api/src/go_service" ] && [ -f "services/api/src/go_service/main.go" ]; then
      echo "path=services/api/src/go_service" >> $GITHUB_OUTPUT
      echo "✓ Found Go service at services/api/src/go_service"
    else
      echo "path=" >> $GITHUB_OUTPUT
      echo "⚠ No Go service found. Checked:"
      echo "  - src/go_service/main.go"
      echo "  - services/api/src/go_service/main.go"
    fi

- name: Build Go service (if present)
  if: steps.gosvc.outputs.path != ''
  run: |
    cd "${{ steps.gosvc.outputs.path }}"
    echo "Building Go service from ${{ steps.gosvc.outputs.path }}"
    go build -v ./...

- name: Note - Go service not present (skip)
  if: steps.gosvc.outputs.path == ''
  run: |
    echo "ℹ️  No Go service directory found. Skipping Go build/test."
    echo "   If you expect a Go service, ensure main.go exists at one of:"
    echo "   - src/go_service/main.go"
    echo "   - services/api/src/go_service/main.go"
```

**Improvements:**
- ✅ Detects Go service in BOTH canonical locations
- ✅ Validates `main.go` exists (not just directory)
- ✅ Conditionally runs build/test only if present
- ✅ Provides clear diagnostic output with paths checked
- ✅ Never fails due to missing directory
- ✅ No `|| true` hacks - proper conditional logic

### 4. Status Documentation
📄 **New File:** `docs/REPLIT_REMOTE_STATUS.md`

Quick reference showing:
- Current git remote configuration
- Recommended approach (Strategy 1)
- Both configuration options
- CI pipeline fix details
- Current Go service location
- Next steps

---

## Verification Results

### Git Remotes (Current State)
```
origin    https://github.com/koneticai/fire-ai.git (fetch)
origin    https://github.com/koneticai/fire-ai.git (push)
replit    NOT CONFIGURED (tools provided for setup)
```

### Go Service Locations (Verified)
```
✓ src/go_service/main.go EXISTS (canonical location)
✗ services/api/src/go_service/main.go MISSING (legacy path)
```

### CI Workflow
```
✓ YAML syntax valid
✓ Go service detection logic implemented
✓ Graceful failure with hints
✓ Python jobs unchanged (services/api)
```

---

## Authoritative References Used

1. **ADR-0001** (`docs/adr/0001-repo-foundation.md`)
   - Confirmed monorepo layout: `services/api` (Python), `src/go_service` (Go)

2. **CI Starter** (`.github/workflows/ci.yml`)
   - Identified failing path: `services/api/src/go_service`
   - Fixed with dual-path detection

3. **Replit Docs** (`replit.md`)
   - Used for context on deployment architecture
   - Enhanced with sync workflows

---

## Constants & Paths

```bash
REPO_ROOT=/Users/alexwilson/Konetic-AI/Projects/FireAI/fire-ai
GO_SVC_CANON=src/go_service                          # ✓ Current location
GO_SVC_LEGACY=services/api/src/go_service            # ✗ Missing (legacy)
REPLIT_REMOTE=replit                                 # Not configured
```

---

## Next Steps for Team

1. **Choose Sync Strategy:**
   ```bash
   # Option A: GitHub Auto-Sync (no action needed)
   # Option B: Direct Push
   ./scripts/setup-replit-remote.sh
   ```

2. **Test CI Pipeline:**
   ```bash
   git add -A
   git commit -m "ci: harden Go service detection"
   git push origin main
   # Check GitHub Actions run
   ```

3. **Update Project-Specific Details:**
   - Add actual Replit project name to docs
   - Configure team-specific sync preferences

---

## Files Created/Modified

### Created (4 files)
- `docs/runbooks/replit-sync.md` - Comprehensive sync runbook
- `scripts/setup-replit-remote.sh` - Interactive setup script
- `docs/REPLIT_REMOTE_STATUS.md` - Quick status reference
- `docs/ATOMIC_REPAIR_SUMMARY.md` - This document

### Modified (1 file)
- `.github/workflows/ci.yml` - Hardened Go service detection

---

## Compliance

✅ Idempotent operations (safe to re-run)  
✅ No credentials committed  
✅ Backward compatible (Python jobs unchanged)  
✅ Clear diagnostics and hints  
✅ Documentation-first approach  
✅ Follows MPKF v3.1 governance

---

## Contact

For questions about this repair:
- See: `docs/runbooks/replit-sync.md` (usage)
- See: `docs/REPLIT_REMOTE_STATUS.md` (status)
- Reference: ADR-0001 (architecture)

