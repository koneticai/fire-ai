#!/bin/bash
set -euo pipefail
echo "=== Fix Storybook builder + rebuild (en-AU, MPKF v3.1) ==="

PKG_DIR="packages/ui"

# 0) Guards
test -d "$PKG_DIR" || { echo "Missing $PKG_DIR — run the scaffold first."; exit 1; }

# 1) Ensure correct Storybook framework (react-vite) + env
echo "→ Writing .storybook/main.ts with @storybook/react-vite"
cat > "$PKG_DIR/.storybook/main.ts" <<'TS'
import type { StorybookConfig } from '@storybook/react-vite';
const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(ts|tsx)'],
  addons: ['@storybook/addon-essentials', '@storybook/addon-a11y'],
  framework: { name: '@storybook/react-vite', options: {} }
};
export default config;
TS

# 2) Fix minor typo in HealthDashboard if present
if grep -q "typTypography" "$PKG_DIR/src/organisms/HealthDashboard.tsx" 2>/dev/null; then
  sed -i.bak 's/typTypography/typography/g' "$PKG_DIR/src/organisms/HealthDashboard.tsx" || true
fi

# 3) Add/react-vite framework dependency
echo "→ Installing @storybook/react-vite (and ensuring vite present)"
pushd "$PKG_DIR" >/dev/null
npm pkg set devDependencies.@storybook/react-vite="^8" >/dev/null
# Ensure vite exists (already set in scaffold, but re-assert here)
npm pkg set devDependencies.vite="^5" >/dev/null

# Create lockfile if missing, then install
if [ -f package-lock.json ]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi

# 4) Build Storybook non-interactively
echo "→ Building Storybook with react-vite builder"
export CI=1 STORYBOOK_DISABLE_TELEMETRY=1 NODE_OPTIONS="--max-old-space-size=4096"
npx storybook build --quiet || npm run build-storybook --silent
popd >/dev/null

# 5) Commit changes (MPKF-compliant)
git add "$PKG_DIR/.storybook/main.ts" "$PKG_DIR/package.json" "$PKG_DIR/package-lock.json" \
        "$PKG_DIR/src/organisms/HealthDashboard.tsx"
git commit -m "chore(ui): fix Storybook builder to @storybook/react-vite + rebuild [FM-ENH-003]

MPKF-Ref: TDD-v4.0-Section-11.5,v3.1
Relates-To: FM-ENH-001,FM-ENH-002,FM-ENH-004,FM-ENH-005" || echo "No changes to commit"

echo "✅ Storybook fixed. You can now push and open the PR; CI a11y gate will run axe ≥95."
