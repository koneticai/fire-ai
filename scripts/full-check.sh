#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/Library/Python/3.13/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

COMMIT_MSG="${COMMIT_MSG:-feat: full validation sync (tests+build+validators+commit+push+replit) [FM-ENH-000]

MPKF-Ref: TDD-v4.0-Section-Impl,v3.1  Relates-To: FM-ENH-001}"
CREATE_PR="${CREATE_PR:-false}"
PUSH_REPLIT="${PUSH_REPLIT:-false}"
REPLIT_BRANCH="${REPLIT_BRANCH:-main}"

poetry_cmd() {
  if command -v poetry >/dev/null 2>&1; then poetry "$@"; return $?; fi
  if python3 -c "import poetry" >/dev/null 2>&1; then python3 -m poetry "$@"; return $?; fi
  return 127
}
ensure_poetry() {
  poetry_cmd --version >/dev/null 2>&1 && return 0
  command -v brew >/dev/null 2>&1 && (brew list poetry >/dev/null 2>&1 || brew install poetry) || true
  python3 -m pip install --user poetry || true
}

git rev-parse --show-toplevel >/dev/null 2>&1 || { echo "❌ Not in a git repo"; exit 1; }
REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
echo "🔎 Repo: $REPO_ROOT"; echo "🔎 Branch: $BRANCH"
git config user.name  >/dev/null 2>&1 || git config user.name  "Alex Wilson"
git config user.email >/dev/null 2>&1 || git config user.email "alex@koneticai.com"

# ---------- Python ----------
if [ -d "services/api" ]; then
  echo "🧪 Python checks (services/api)"
  pushd services/api >/dev/null
  if [ -f "pyproject.toml" ] || [ -f "poetry.lock" ]; then
    ensure_poetry
    if poetry_cmd --version >/dev/null 2>&1; then
      # tolerate non-packaged projects
      poetry_cmd install --no-root

      poetry_cmd run ruff --version   >/dev/null 2>&1 && poetry_cmd run ruff check .
      poetry_cmd run black --version  >/dev/null 2>&1 && poetry_cmd run black --check .
      poetry_cmd run pylint --version >/dev/null 2>&1 && [ -d "src" ] && poetry_cmd run pylint $(git ls-files 'src/**/*.py') || true

      if poetry_cmd run pytest --version >/dev/null 2>&1; then
        if poetry_cmd run python - <<'PY' >/dev/null 2>&1; then
import importlib, sys
sys.exit(0 if importlib.util.find_spec('pytest_cov') else 1)
PY
          poetry_cmd run pytest --cov=src --cov-report=term-missing --cov-fail-under=80
        else
          poetry_cmd run pytest -q
        fi
      fi

      if poetry_cmd run pip-audit --version >/dev/null 2>&1; then
        poetry_cmd export -f requirements.txt --without-hashes | poetry_cmd run pip-audit -r /dev/stdin --strict || true
      else
        python3 -m pip install --user safety >/dev/null 2>&1 || true
        poetry_cmd export -f requirements.txt --without-hashes | safety check --stdin --full-report || true
      fi
    else
      echo "⚠️  Poetry unavailable; skipping Python checks."
    fi
  else
    echo "ℹ️  No pyproject/poetry.lock; skipping Python."
  fi
  popd >/dev/null
else
  echo "ℹ️  services/api missing — skipping Python."
fi

# ---------- Go ----------
if [ -d "services/api/src/go_service" ]; then
  echo "🧰 Go checks (services/api/src/go_service)"
  pushd services/api/src/go_service >/dev/null
  if command -v go >/dev/null 2>&1; then
    go mod download; go vet ./...; go test -v ./...
  else
    echo "ℹ️  Go not installed; skipping."
  fi
  popd >/dev/null
fi

# ---------- MPKF ----------
if [ -x "scripts/validate-mpkf.sh" ]; then
  echo "🔏 MPKF validation"; ./scripts/validate-mpkf.sh
else
  echo "ℹ️  scripts/validate-mpkf.sh missing; skipping."
fi

# ---------- Commit ----------
if ! git diff --quiet --staged || ! git diff --quiet; then
  echo "📝 Staging & committing"; git add -A; git commit -m "$COMMIT_MSG" || true
else
  echo "ℹ️  No changes to commit."
fi

# ---------- Push ----------
echo "⬇️  Pull (rebase) origin/$BRANCH"; git fetch origin "$BRANCH" || true; git pull --rebase origin "$BRANCH" || true
echo "⬆️  Push origin/$BRANCH"; git push -u origin "$BRANCH"

# ---------- Replit (optional) ----------
if [ "${PUSH_REPLIT}" = "true" ] && git remote get-url replit >/dev/null 2>&1; then
  echo "⬆️  Push to replit/$REPLIT_BRANCH"; git push replit "$BRANCH:$REPLIT_BRANCH" || true
fi

# ---------- PR (optional) ----------
if [ "${CREATE_PR}" = "true" ] && command -v gh >/dev/null 2>&1; then
  echo "🔀 Creating PR via gh"; gh pr create --fill --base main --head "$BRANCH" || true
fi

echo "✅ Full check completed."
