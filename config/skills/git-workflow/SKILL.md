---
name: git-workflow
category: development
description: Git workflow conventions — branching, committing, and pushing
---

# Git Workflow Skill

## Conventions

- Write concise, action-oriented commit messages (e.g., `Add search_files tool`)
- Group related changes into logical commits
- Run tests before committing
- Check `git status` before and after operations

## Common Commands

```bash
# Check status
git status

# Stage and commit
git add <files>
git commit -m "Concise message"

# Push
git push

# Pull with rebase
git pull --rebase

# Create branch
git checkout -b feature/name

# Diff
git diff
git diff --staged
```

## Pitfalls

- Don't commit large, unrelated changes in a single commit
- Don't push without running tests first
- Don't use `git push --force` unless you understand the consequences
- Always check for uncommitted changes before switching branches
