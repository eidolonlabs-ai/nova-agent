---
name: git-workflow
category: development
description: Git and GitHub workflow — conventional commits, branching, PRs, and gh CLI usage
---

# Git Workflow Skill

## Commit Message Convention

Nova Agent uses **conventional commits**:

```
<type>: <subject>

<body (optional)>
```

Types: `feat` (new feature), `fix` (bug fix), `docs` (docs only), `test` (tests only), `refactor` (no behavior change), `chore` (maintenance)

Rules:
- Subject line: imperative mood, under 72 chars, no trailing period
- Body: optional, use when the *why* isn't obvious from the subject
- Never mix types — a commit that adds a feature AND fixes a bug should be two commits

Examples:
```
feat: add semantic symbol search tool
fix: handle empty context files gracefully
test: expand CLI coverage to 82%
refactor: extract token budget logic into tokens.py
docs: update test counts to reflect 596 tests
```

## Pre-Commit Checklist

Always run the full CI check before committing:

```bash
ruff check . && ruff format --check . && mypy nova/ && pytest
```

If any step fails, fix it before committing. Never commit broken code.

## Workflow

1. `git status` — understand current state
2. Make changes
3. `ruff check . && ruff format --check . && mypy nova/ && pytest` — full CI check must pass
4. `git diff --staged` — review exactly what you're committing
5. `git add <specific files>` — stage intentionally, never `git add .`
6. `git commit -m "type: subject"` — follow conventional commits
7. `git push` (or `git push -u origin HEAD` for new branches)

## Branching

```bash
git checkout -b feat/short-description   # new feature
git checkout -b fix/short-description    # bug fix
git switch main                          # return to main
git pull --rebase                        # sync with remote
git branch -d feat/short-description     # clean up merged branch
```

## GitHub CLI — PRs

```bash
# Create a PR
gh pr create --title "feat: add X" --body "$(cat <<'EOF'
## Summary
- What changed and why

## Test plan
- [ ] All 596 tests pass (`pytest`)
- [ ] Lint clean (`ruff check .`)
- [ ] Format clean (`ruff format --check .`)
- [ ] Types clean (`mypy nova/`)
- [ ] No CVEs (`pip-audit`)
EOF
)"

# List open PRs
gh pr list

# View a PR
gh pr view 42

# Check PR status/CI
gh pr checks 42

# Merge a PR
gh pr merge 42 --squash

# Close without merging
gh pr close 42
```

## GitHub CLI — Reviews

```bash
# View PR diff
gh pr diff 42

# Approve
gh pr review 42 --approve

# Request changes
gh pr review 42 --request-changes --body "See inline comments"

# Leave a comment (no vote)
gh pr review 42 --comment --body "LGTM with nits"

# Add inline comment (requires API)
gh api repos/{owner}/{repo}/pulls/42/comments \
  --method POST \
  --field body="Comment text" \
  --field path="nova/agent.py" \
  --field line=42
```

## GitHub CLI — Issues

```bash
gh issue list
gh issue view 12
gh issue create --title "Bug: X fails when Y" --body "..."
gh issue close 12
gh issue comment 12 --body "Fixed in #43"
```

## Common Git Commands

```bash
git log --oneline -10          # recent commits
git show HEAD                  # show last commit
git diff                       # unstaged changes
git diff --staged              # staged changes
git blame nova/agent.py        # who changed each line
git log --follow nova/agent.py # file history

# Safe undo
git restore <file>             # discard unstaged changes
git restore --staged <file>    # unstage
git revert HEAD                # revert last commit (safe on shared branches)
git stash / git stash pop      # temporarily shelve changes
```

## Pitfalls

- Never `git add .` — always stage specific files
- Never `git push --force` on shared branches — use `--force-with-lease` if you must
- Don't commit without running the full CI check first
- Don't commit secrets, `.env`, or API keys
- Don't mix whitespace-only changes with logic changes in the same commit
- Don't amend commits that have already been pushed
