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
