---
name: git-workflow
category: development
description: Git workflow conventions — branching, committing, pushing, and common operations
---

# Git Workflow Skill

## Commit Message Conventions

- Use imperative mood: `Add search_files tool`, not `Added` or `Adding`
- Keep the subject line under 72 characters
- Group related changes into one logical commit — don't mix unrelated fixes
- Reference issue numbers when relevant: `Fix timeout bug (#42)`

## Workflow

1. Check status before starting: `git status`
2. Make changes
3. Run tests: `pytest` (or project-specific check)
4. Stage intentionally: `git add <specific files>` not `git add .`
5. Review staged diff: `git diff --staged`
6. Commit with a clear message
7. Push

## Common Commands

```bash
# Status and diff
git status
git diff                    # unstaged changes
git diff --staged           # staged changes
git log --oneline -10       # recent commits

# Staging and committing
git add path/to/file        # stage specific file
git add -p                  # interactive staging (review hunks)
git commit -m "Add feature X"
git commit --amend          # fix last commit message (before push)

# Branching
git checkout -b feature/name
git switch main             # switch to main
git branch -d feature/name  # delete merged branch

# Syncing
git pull --rebase           # pull and rebase local commits on top
git fetch origin            # fetch without merging
git push
git push -u origin HEAD     # push new branch and set upstream

# Undoing
git restore <file>          # discard unstaged changes to a file
git restore --staged <file> # unstage a file
git revert HEAD             # create a revert commit (safe for shared branches)
git stash                   # stash uncommitted changes
git stash pop               # restore stashed changes

# Inspection
git show HEAD               # show last commit
git blame path/to/file      # who changed each line
git log --follow path/to/file  # history of a file
```

## Pitfalls

- Never `git add .` blindly — always review what you're staging
- Don't commit secrets, API keys, or `.env` files
- Don't use `git push --force` on shared branches — use `--force-with-lease` if you must
- Don't commit broken code — run tests first
- Don't mix whitespace-only changes with logic changes in the same commit
- Always check for uncommitted changes before switching branches (`git status`)
