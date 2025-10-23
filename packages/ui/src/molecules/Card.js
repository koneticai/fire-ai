import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { tokens } from '../tokens';
export const Card = ({ title, children }) => (_jsxs("section", { role: "region", "aria-label": title ?? 'Card', style: {
        padding: tokens.spacing.md, borderRadius: tokens.radius.lg, background: '#FFF', boxShadow: tokens.shadow.md
    }, children: [title ? _jsx("h2", { style: { fontSize: tokens.typography.fontSize.lg, marginTop: 0 }, children: title }) : null, children] }));
