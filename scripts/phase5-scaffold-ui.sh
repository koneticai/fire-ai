#!/bin/bash
set -euo pipefail

echo "=== Fire-AI Phase 5: UI Scaffold + Storybook (lockfile-aware) ==="

# 0) Guard: ensure git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not a git repo"; exit 1; }

# 1) Create package structure
mkdir -p packages/ui/src/{tokens,atoms,molecules,organisms,stories} packages/ui/.storybook

# 2) .gitignore (avoid node_modules noise)
if [ ! -f packages/ui/.gitignore ]; then
  cat > packages/ui/.gitignore <<'IG'
node_modules
dist
storybook-static
IG
fi

# 3) package.json (same as before)
cat > packages/ui/package.json <<'JSON'
{
  "name": "@fire-ai/ui",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc -p tsconfig.build.json",
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build --quiet",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@storybook/react": "^8.1.0",
    "@storybook/addon-a11y": "^8.1.0",
    "@storybook/addon-essentials": "^8.1.0",
    "vite": "^5.0.0",
    "vitest": "^1.6.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@axe-core/cli": "^4.9.0"
  }
}
JSON

# 4) tsconfigs
cat > packages/ui/tsconfig.build.json <<'JSON'
{
  "extends": "./tsconfig.json",
  "compilerOptions": { "outDir": "dist", "declaration": true, "emitDeclarationOnly": true },
  "include": ["src"]
}
JSON

cat > packages/ui/tsconfig.json <<'JSON'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "jsx": "react-jsx",
    "strict": true,
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "lib": ["ES2022", "DOM"]
  },
  "include": ["src"]
}
JSON

# 5) tokens + atoms/molecules/organisms + stories + storybook config
# (unchanged content from the previous scaffold)
cat > packages/ui/src/tokens/index.ts <<'TS'
export const tokens = {
  colors: {
    primary: '#0066CC',
    secondary: '#6C757D',
    success: '#28A745',
    warning: '#FFC107',
    danger:  '#DC3545',
    text: { primary: '#212529', secondary: '#6C757D', inverse: '#FFFFFF' }
  },
  spacing: { xs:'0.25rem', sm:'0.5rem', md:'1rem', lg:'1.5rem', xl:'2rem' },
  typography: {
    fontFamily: { sans: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif', mono: 'Monaco, Courier, monospace' },
    fontSize: { xs:'0.75rem', sm:'0.875rem', base:'1rem', lg:'1.125rem', xl:'1.25rem' }
  },
  radius: { sm:'0.25rem', md:'0.5rem', lg:'1rem' },
  shadow: { sm:'0 1px 2px rgba(0,0,0,0.08)', md:'0 4px 12px rgba(0,0,0,0.10)' }
} as const;
TS

cat > packages/ui/src/atoms/Button.tsx <<'TSX'
import * as React from 'react';
import { tokens } from '../tokens';
export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary'; };
export const Button: React.FC<ButtonProps> = ({ variant='primary', children, ...rest }) => {
  const bg = variant === 'primary' ? tokens.colors.primary : tokens.colors.secondary;
  return (
    <button {...rest} className="fm-btn" style={{
      background: bg, color: tokens.colors.text.inverse, padding: `${tokens.spacing.sm} ${tokens.spacing.md}`,
      borderRadius: tokens.radius.md, border: 0
    }}>{children}</button>
  );
};
TSX

cat > packages/ui/src/atoms/Input.tsx <<'TSX'
import * as React from 'react';
import { tokens } from '../tokens';
export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;
export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(props, ref) {
  return (
    <input ref={ref} {...props} style={{
      padding: tokens.spacing.sm, borderRadius: tokens.radius.sm, border: '1px solid #CED4DA',
      fontFamily: tokens.typography.fontFamily.sans
    }}/>
  );
});
TSX

cat > packages/ui/src/molecules/Card.tsx <<'TSX'
import * as React from 'react';
import { tokens } from '../tokens';
export const Card: React.FC<React.PropsWithChildren<{title?: string}>> = ({ title, children }) => (
  <section role="region" aria-label={title ?? 'Card'} style={{
    padding: tokens.spacing.md, borderRadius: tokens.radius.lg, background: '#FFF', boxShadow: tokens.shadow.md
  }}>
    {title ? <h2 style={{ fontSize: tokens.typography.fontSize.lg, marginTop: 0 }}>{title}</h2> : null}
    {children}
  </section>
);
TSX

cat > packages/ui/src/organisms/CostOverview.tsx <<'TSX'
import * as React from 'react';
import { tokens } from '../tokens';
export const CostOverview: React.FC = () => (
  <section role="region" aria-label="Cost Overview" aria-live="polite" style={{ padding: tokens.spacing.md }}>
    <h1 style={{ fontSize: tokens.typography.fontSize.xl, marginTop: 0 }}>Cost Overview</h1>
    <p>Total (mock): $12,345</p>
    <div role="progressbar" aria-valuenow={70} aria-valuemin={0} aria-valuemax={100} aria-label="Budget used"
         style={{ height: 12, background: '#E9ECEF', borderRadius: 6 }}>
      <div style={{ width: '70%', height: '100%', background: tokens.colors.warning, borderRadius: 6 }} />
    </div>
  </section>
);
TSX

cat > packages/ui/src/organisms/HealthDashboard.tsx <<'TSX'
import * as React from 'react';
import { tokens } from '../tokens';
export const HealthDashboard: React.FC = () => (
  <section role="region" aria-label="Health Status" style={{ padding: tokens.spacing.md }}>
    <h1 style={{ fontSize: tokens.typTypography?.fontSize?.xl ?? tokens.typography.fontSize.xl, marginTop: 0 }}>Health Status</h1>
    <p role="status" aria-live="polite">All systems nominal.</p>
  </section>
);
TSX

cat > packages/ui/src/organisms/SchemaRegistry.tsx <<'TSX'
import * as React from 'react';
import { tokens } from '../tokens';
import { Input } from '../atoms/Input';
export const SchemaRegistry: React.FC = () => (
  <section role="region" aria-label="Schema Registry" style={{ padding: tokens.spacing.md }}>
    <h1 style={{ fontSize: tokens.typography.fontSize.xl, marginTop: 0 }}>Schema Registry</h1>
    <form aria-labelledby="schema-form">
      <div style={{ marginBottom: tokens.spacing.sm }}>
        <label htmlFor="schemaName">Schema name</label><br />
        <Input id="schemaName" name="schemaName" aria-describedby="schemaNameHelp" />
        <div id="schemaNameHelp">Provide a unique, descriptive name.</div>
      </div>
      <div role="alert" aria-live="assertive" style={{ display: 'none' }}>Validation error will appear here</div>
      <button type="submit" style={{ marginTop: tokens.spacing.sm }}>Save</button>
    </form>
  </section>
);
TSX

cat > packages/ui/src/organisms/DRStatus.tsx <<'TSX'
import * as React from 'react';
import { tokens } from '../tokens';
export const DRStatus: React.FC = () => (
  <section role="region" aria-label="DR Status Panel" style={{ padding: tokens.spacing.md }}>
    <h1 style={{ fontSize: tokens.typography.fontSize.xl, marginTop: 0 }}>DR Status</h1>
    <div role="alert">No incidents.</div>
    <ul><li><a href="#" onClick={(e) => e.preventDefault()}>Run DR drill (stub)</a></li></ul>
  </section>
);
TSX

cat > packages/ui/src/index.ts <<'TS'
export * from './tokens';
export * from './atoms/Button';
export * from './atoms/Input';
export * from './molecules/Card';
export * from './organisms/CostOverview';
export * from './organisms/HealthDashboard';
export * from './organisms/SchemaRegistry';
export * from './organisms/DRStatus';
TS

cat > packages/ui/.storybook/main.ts <<'TS'
import type { StorybookConfig } from '@storybook/react';
const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(ts|tsx)'],
  addons: ['@storybook/addon-essentials', '@storybook/addon-a11y'],
  framework: { name: '@storybook/react', options: {} }
};
export default config;
TS

cat > packages/ui/.storybook/preview.ts <<'TS'
import type { Preview } from '@storybook/react';
const preview: Preview = { parameters: { a11y: { disable: false } } };
export default preview;
TS

cat > packages/ui/src/stories/hello-tokens.stories.tsx <<'TSX'
import type { Meta, StoryObj } from '@storybook/react';
import { tokens } from '../tokens';
const meta: Meta = { title: 'Foundations/Hello Tokens', parameters: { a11y: { disable: false } } };
export default meta;
export const Overview: StoryObj = {
  render: () => (
    <div style={{ fontFamily: tokens.typography.fontFamily.sans, padding: tokens.spacing.lg, background: '#FFF' }}>
      <h1 style={{ fontSize: tokens.typography.fontSize.xl }}>Hello Tokens</h1>
      <p style={{ fontSize: tokens.typography.fontSize.base, color: tokens.colors.text.primary }}>
        This page demonstrates design tokens and basic contrast pairs.
      </p>
      <div aria-label="Token swatches" role="list">
        {(['primary','secondary','success','warning','danger'] as const).map(k => (
          <div key={k} role="listitem" style={{ marginBottom: tokens.spacing.sm }}>
            <span style={{ display:'inline-block', width: 96, height: 24, background: (tokens.colors as any)[k], boxShadow: tokens.shadow.sm }} />
            <span style={{ marginLeft: tokens.spacing.sm }}>{k}</span>
          </div>
        ))}
      </div>
    </div>
  )
};
TSX

cat > packages/ui/src/stories/button.stories.tsx <<'TSX'
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '../atoms/Button';
const meta: Meta<typeof Button> = { title: 'Atoms/Button', component: Button };
export default meta;
export const Primary: StoryObj<typeof Button> = { args: { children: 'Primary', variant: 'primary' } };
export const Secondary: StoryObj<typeof Button> = { args: { children: 'Secondary', variant: 'secondary' } };
TSX

cat > packages/ui/src/stories/cost-overview.stories.tsx <<'TSX'
import type { Meta, StoryObj } from '@storybook/react';
import { CostOverview } from '../organisms/CostOverview';
const meta: Meta<typeof CostOverview> = { title: 'Organisms/CostOverview', component: CostOverview };
export default meta;
export const Default: StoryObj<typeof CostOverview> = {};
TSX

# 6) Install deps with lockfile generation (handles your error)
echo "→ Installing deps and generating lockfile..."
pushd packages/ui >/dev/null
if [ -f package-lock.json ]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi

# 7) Build Storybook once (optional; CI will also build)
echo "→ Building Storybook..."
npx storybook build --quiet || npm run build-storybook --silent
popd >/dev/null

# 8) Commit all UI files including package-lock.json (MPKF-compliant)
git add packages/ui
git commit -m "feat(ui): scaffold tokens + Storybook + accessible stubs [FM-ENH-003]

MPKF-Ref: TDD-v4.0-Section-11.5,v3.1
Relates-To: FM-ENH-001,FM-ENH-002,FM-ENH-004,FM-ENH-005" || echo "No changes to commit"

echo "✅ UI scaffold complete. You can now push and open your PR."
