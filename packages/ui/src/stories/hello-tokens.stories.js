import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { tokens } from '../tokens';
const meta = { title: 'Foundations/Hello Tokens', parameters: { a11y: { disable: false } } };
export default meta;
export const Overview = {
    render: () => (_jsxs("div", { style: { fontFamily: tokens.typography.fontFamily.sans, padding: tokens.spacing.lg, background: '#FFF' }, children: [_jsx("h1", { style: { fontSize: tokens.typography.fontSize.xl }, children: "Hello Tokens" }), _jsx("p", { style: { fontSize: tokens.typography.fontSize.base, color: tokens.colors.text.primary }, children: "This page demonstrates design tokens and basic contrast pairs." }), _jsx("div", { "aria-label": "Token swatches", role: "list", children: ['primary', 'secondary', 'success', 'warning', 'danger'].map(k => (_jsxs("div", { role: "listitem", style: { marginBottom: tokens.spacing.sm }, children: [_jsx("span", { style: { display: 'inline-block', width: 96, height: 24, background: tokens.colors[k], boxShadow: tokens.shadow.sm } }), _jsx("span", { style: { marginLeft: tokens.spacing.sm }, children: k })] }, k))) })] }))
};
