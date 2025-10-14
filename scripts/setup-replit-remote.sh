#!/bin/bash
# Setup Replit Git Remote
# Usage: ./scripts/setup-replit-remote.sh [username] [token] [project]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "🔧 Replit Remote Setup"
echo "======================"
echo ""

# Check if replit remote already exists
if git remote | grep -q '^replit$'; then
    echo "⚠️  Replit remote already exists:"
    git remote get-url replit
    echo ""
    read -p "Remove and re-add? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove replit
        echo "✓ Removed existing replit remote"
    else
        echo "❌ Aborted"
        exit 1
    fi
fi

# Get credentials
if [ $# -eq 3 ]; then
    REPLIT_USERNAME="$1"
    REPLIT_TOKEN="$2"
    REPLIT_PROJECT="$3"
else
    echo "Enter your Replit credentials:"
    echo "(Get your Git token from: Profile → Account → Generate Git Token)"
    echo ""
    
    read -p "Replit username: " REPLIT_USERNAME
    read -sp "Replit Git token: " REPLIT_TOKEN
    echo ""
    read -p "Replit project name: " REPLIT_PROJECT
fi

if [ -z "$REPLIT_USERNAME" ] || [ -z "$REPLIT_TOKEN" ] || [ -z "$REPLIT_PROJECT" ]; then
    echo "❌ All fields are required"
    exit 1
fi

# Add remote
REPLIT_URL="https://${REPLIT_USERNAME}:${REPLIT_TOKEN}@git.replit.com/${REPLIT_PROJECT}.git"
git remote add replit "$REPLIT_URL"

echo ""
echo "✓ Replit remote added successfully!"
echo ""
echo "Current remotes:"
git remote -v | sed "s/${REPLIT_TOKEN}/***/g"
echo ""
echo "📖 Usage:"
echo "  git push replit main      # Push to Replit"
echo "  git pull replit main      # Pull from Replit"
echo ""
echo "📚 See docs/runbooks/replit-sync.md for full workflow"

