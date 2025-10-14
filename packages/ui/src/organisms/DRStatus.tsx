import * as React from 'react';
import { tokens } from '../tokens';
export const DRStatus: React.FC = () => (
  <section role="region" aria-label="DR Status Panel" style={{ padding: tokens.spacing.md }}>
    <h1 style={{ fontSize: tokens.typography.fontSize.xl, marginTop: 0 }}>DR Status</h1>
    <div role="alert">No incidents.</div>
    <ul><li><a href="#" onClick={(e) => e.preventDefault()}>Run DR drill (stub)</a></li></ul>
  </section>
);
