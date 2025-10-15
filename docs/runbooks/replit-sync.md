# Replit Sync Runbook

**Purpose:** Configure and maintain bi-directional sync between GitHub, Local/Cursor, and Replit.

**Last Updated:** 2025-10-14  
**Owner:** Platform Team

---

## Overview

Fire-AI supports two synchronization strategies with Replit:

1. **GitHub Auto-Sync (Recommended):** Let Replit automatically sync from GitHub
2. **Direct Push:** Configure Replit as a git remote for direct push/pull

---

## Strategy 1: GitHub Auto-Sync (Recommended)

### Setup
1. In Replit workspace, connect to GitHub repository:
   - Open Replit project
   - Go to Version Control → Connect to GitHub
   - Authorize and select `koneticai/fire-ai` repository

2. Replit will automatically pull changes from GitHub on:
   - Manual "Pull from GitHub" button click
   - Workspace restart (optional auto-sync)

### Workflow
```bash
# Local development flow
git add .
git commit -m "feat: add feature X"
git push origin main

# Replit updates automatically or via UI pull
```

**Pros:**
- No credential management
- Simplified workflow
- GitHub remains single source of truth

**Cons:**
- Requires manual pull in Replit UI
- No direct Replit → GitHub push

---

## Strategy 2: Direct Push via Remote

### Prerequisites
- Replit account with Git access enabled
- Personal Access Token (PAT) from Replit:
  - Profile → Account → Generate Git Token

### Setup
```bash
# Add Replit remote (one-time setup)
git remote add replit https://<REPLIT_USERNAME>:<REPLIT_TOKEN>@git.replit.com/<REPLIT_PROJECT_NAME>.git

# Verify remotes
git remote -v
# Expected output:
# origin    git@github.com:koneticai/fire-ai.git (fetch)
# origin    git@github.com:koneticai/fire-ai.git (push)
# replit    https://<username>:***@git.replit.com/<project>.git (fetch)
# replit    https://<username>:***@git.replit.com/<project>.git (push)
```

### Workflow
```bash
# Local → GitHub → Replit
git add .
git commit -m "feat: add feature X"
git push origin main          # Push to GitHub
git push replit main          # Push to Replit

# Replit → Local
git pull replit main          # Pull Replit changes
git push origin main          # Sync to GitHub

# Sync alias (add to ~/.gitconfig or ~/.zshrc)
alias git-sync-all='git push origin main && git push replit main'
```

### Bi-directional Sync Example
```bash
# Scenario: Changes in Replit workspace
cd /path/to/fire-ai
git pull replit main                    # Pull Replit changes
git merge --no-ff replit/main -m "sync: merge Replit changes"
git push origin main                     # Push merged changes to GitHub

# Scenario: Changes in Local/Cursor
git add .
git commit -m "fix: resolve CI issue"
git push origin main                     # Push to GitHub first
git push replit main                     # Then push to Replit
```

---

## Troubleshooting

### Remote already exists
```bash
git remote remove replit
git remote add replit https://<username>:<token>@git.replit.com/<project>.git
```

### Authentication failure
1. Regenerate Replit PAT
2. Update remote URL:
   ```bash
   git remote set-url replit https://<username>:<NEW_TOKEN>@git.replit.com/<project>.git
   ```

### Divergent branches
```bash
# If Replit and origin diverge
git fetch replit
git fetch origin
git merge origin/main replit/main --no-ff
git push origin main
git push replit main
```

### Verify sync status
```bash
# Check all remote branches
git remote -v
git branch -r

# Compare local with remotes
git log origin/main..HEAD              # Commits not yet pushed to GitHub
git log replit/main..HEAD              # Commits not yet pushed to Replit
```

---

## Current Configuration

**Repository:** `koneticai/fire-ai`  
**Default Strategy:** GitHub Auto-Sync (Strategy 1)  
**Replit Remote:** Not configured (manual setup required for Strategy 2)

To enable Strategy 2, run:
```bash
cd /Users/alexwilson/Konetic-AI/Projects/FireAI/fire-ai
git remote add replit https://<REPLIT_USERNAME>:<REPLIT_TOKEN>@git.replit.com/<REPLIT_PROJECT_NAME>.git
```

---

## References
- [ADR-0001: Repository Foundation](../adr/0001-repo-foundation.md)
- [Replit Git Documentation](https://docs.replit.com/programming-ide/using-git-on-replit)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)

