import { jsx as _jsx } from "react/jsx-runtime";
import { tokens } from '../tokens';
export const Button = ({ variant = 'primary', children, ...rest }) => {
    const bg = variant === 'primary' ? tokens.colors.primary : tokens.colors.secondary;
    return (_jsx("button", { ...rest, className: "fm-btn", style: {
            background: bg, color: tokens.colors.text.inverse, padding: `${tokens.spacing.sm} ${tokens.spacing.md}`,
            borderRadius: tokens.radius.md, border: 0
        }, children: children }));
};
