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
