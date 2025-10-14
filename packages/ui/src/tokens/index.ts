export const tokens = {
  colors: {
    primary: '#0066CC',
    secondary: '#6C757D',
    success: '#28A745',
    warning: '#FFC107',
    danger:  '#DC3545',
    text: { primary: '#212529', secondary: '#6C757D', inverse: '#FFFFFF' }
  },
  spacing: { xs:'0.25rem', sm:'0.5rem', md:'1rem', lg:'1.5rem', xl:'2rem' },
  typography: {
    fontFamily: { sans: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif', mono: 'Monaco, Courier, monospace' },
    fontSize: { xs:'0.75rem', sm:'0.875rem', base:'1rem', lg:'1.125rem', xl:'1.25rem' }
  },
  radius: { sm:'0.25rem', md:'0.5rem', lg:'1rem' },
  shadow: { sm:'0 1px 2px rgba(0,0,0,0.08)', md:'0 4px 12px rgba(0,0,0,0.10)' }
} as const;
