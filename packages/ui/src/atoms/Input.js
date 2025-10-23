import { jsx as _jsx } from "react/jsx-runtime";
import * as React from 'react';
import { tokens } from '../tokens';
export const Input = React.forwardRef(function Input(props, ref) {
    return (_jsx("input", { ref: ref, ...props, style: {
            padding: tokens.spacing.sm, borderRadius: tokens.radius.sm, border: '1px solid #CED4DA',
            fontFamily: tokens.typography.fontFamily.sans
        } }));
});
