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
