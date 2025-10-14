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
