import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { tokens } from '../tokens';
export const DRStatus = () => (_jsxs("section", { role: "region", "aria-label": "DR Status Panel", style: { padding: tokens.spacing.md }, children: [_jsx("h1", { style: { fontSize: tokens.typography.fontSize.xl, marginTop: 0 }, children: "DR Status" }), _jsx("div", { role: "alert", children: "No incidents." }), _jsx("ul", { children: _jsx("li", { children: _jsx("a", { href: "#", onClick: (e) => e.preventDefault(), children: "Run DR drill (stub)" }) }) })] }));
