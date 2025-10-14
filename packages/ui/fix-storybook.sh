#!/bin/bash
# Run from packages/ui directory

echo "🧹 Cleaning environment..."
rm -rf node_modules package-lock.json storybook-static .storybook-cache

echo "📝 Creating clean package.json..."
cat > package.json << 'EOF'
{
  "name": "@fire-ai/ui",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "storybook dev -p 6006",
    "build": "tsc && vite build",
    "build-storybook": "storybook build",
    "test": "jest",
    "lint": "eslint src --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@storybook/addon-a11y": "^8.6.14",
    "@storybook/addon-essentials": "^8.6.14",
    "@storybook/addon-links": "^8.6.14",
    "@storybook/react": "^8.6.14",
    "@storybook/react-vite": "^8.6.14",
    "@types/react": "^18.2.79",
    "@types/react-dom": "^18.2.25",
    "storybook": "^8.6.14",
    "typescript": "^5.4.5",
    "vite": "^5.2.11"
  },
  "peerDependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
EOF

echo "📦 Installing dependencies..."
npm install

echo "🔨 Building Storybook..."
npm run build-storybook

echo "✅ Done! Verify with: npx axe --dir storybook-static --threshold 95"