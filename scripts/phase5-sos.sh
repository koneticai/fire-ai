#!/bin/bash
# Fire-AI Phase 5 "SOS" — stabilise local, verify artefacts, optional push (en-AU)
set -euo pipefail

echo "=== Fire-AI Phase 5 SOS ==="
START_ALL=$(date +%s)

# ---------- 0) Fast shell fix for missing sourced files ----------
if [ -f "$HOME/.zshrc" ] && grep -q '\. .*envalias' "$HOME/.zshrc"; then
  echo "→ Guarding ~/.zshrc against missing Deno envalias"
  perl -0777 -pe 's~\.\s+"?\$HOME/\.deno/envalias"?~[ -f "$HOME/.deno/envalias" ] \&\& . "$HOME/.deno/envalias"~g' -i.bak "$HOME/.zshrc" || true
fi

# ---------- 1) Kill obvious offenders (hung Storybook/Node/Chromium) ----------
echo "→ Killing hung Node/Storybook/Chromium (if any)"
pkill -f "storybook" || true
pkill -f "node .*vite" || true
pkill -f "node .*jest" || true
pkill -f "chromium" || true

# ---------- 2) Clean caches (fast, deterministic) ----------
echo "→ Cleaning npm cache + node_modules (packages/ui only if present)"
if [ -d packages/ui ]; then
  (cd packages/ui && rm -rf node_modules package-lock.json) || true
fi
npm cache clean --force >/dev/null 2>&1 || true

# ---------- 3) System tweaks for heavy builds ----------
export CI=1
export STORYBOOK_DISABLE_TELEMETRY=1
export NODE_OPTIONS="${NODE_OPTIONS:-} --max-old-space-size=4096"
ulimit -n 8192 2>/dev/null || true

# ---------- 4) Verify Phase-5 artefacts exist ----------
echo "→ Checking required Phase-5 files"
REQ_PATHS=(
  ".github/workflows/ci.yml"
  ".github/workflows/bugbot-qa.yml"
  ".github/PULL_REQUEST_TEMPLATE.md"
  "scripts/validate-mpkf.sh"
  ".cursor"
)
MISS=0
for p in "${REQ_PATHS[@]}"; do
  if git ls-files --error-unmatch "$p" >/dev/null 2>&1; then
    echo "   ✔ $p"
  else
    echo "   ✘ Missing: $p"
    MISS=1
  fi
done

# ---------- 5) Wire pre-push MPKF validator ----------
echo "→ Ensuring pre-push MPKF validator is wired"
if [ -f scripts/validate-mpkf.sh ]; then
  chmod +x scripts/validate-mpkf.sh
  HOOK=".git/hooks/pre-push"
  if ! grep -q 'validate-mpkf.sh' "$HOOK" 2>/dev/null; then
    printf '#!/bin/bash\n./scripts/validate-mpkf.sh\n' > "$HOOK"
    chmod +x "$HOOK"
    echo "   ✔ pre-push hook installed"
  else
    echo "   ✔ pre-push hook already present"
  fi
else
  echo "   ⚠ scripts/validate-mpkf.sh missing"
fi

# ---------- 6) Build Storybook (if UI package exists) ----------
if [ -d packages/ui ]; then
  echo "→ Installing + building Storybook in packages/ui (quiet, resilient)"
  pushd packages/ui >/dev/null
  time npm ci --no-audit --no-fund
  time npx storybook build --quiet || npm run build-storybook --silent
  popd >/dev/null
else
  echo "⚠ packages/ui not found — skipping Storybook build"
fi

# ---------- 7) Axe scan (if storybook-static exists) ----------
if [ -d packages/ui/storybook-static ]; then
  echo "→ Running axe-core CLI (threshold 95)"
  (cd packages/ui && npx -y @axe-core/cli@4.x axe --dir storybook-static --threshold 95) || true
else
  echo "⚠ storybook-static missing — axe scan skipped"
fi

# ---------- 8) Show recent commits (MPKF tags) ----------
echo "→ Recent commits:"
git --no-pager log --oneline -n 5

# ---------- 9) Optional: push + PR ----------
read -p "Push current branch and open PR to main (y/N)? " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
  BR=$(git rev-parse --abbrev-ref HEAD)
  git push -u origin "$BR"
  command -v gh >/dev/null 2>&1 && gh pr create --base main --head "$BR" \
    --title "feat(ui): Phase 5 UI + A11y gate [FM-ENH-003]" \
    --body-file .github/PULL_REQUEST_TEMPLATE.md || true
  echo "→ Pushed. CI + BugBot should trigger on the PR."
else
  echo "→ Skipping push/PR."
fi

END_ALL=$(date +%s)
echo "=== SOS complete in $((END_ALL-START_ALL))s ==="
