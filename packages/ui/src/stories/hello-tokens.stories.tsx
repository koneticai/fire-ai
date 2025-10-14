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
