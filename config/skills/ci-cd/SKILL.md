---
name: ci-cd
category: devops
description: CI/CD pipelines and release automation — lint/type/test/coverage gates, GitHub Actions, semantic versioning, changelogs, and rollback
---

# CI/CD Skill

Every push goes through the same gates as a release. If it doesn't pass CI, it doesn't merge.

## Pipeline Stages (in order)

1. **Lint** — `ruff check .`
2. **Format** — `ruff format --check .`
3. **Types** — `mypy nova/`
4. **Tests** — `pytest` with coverage gate (`pytest --cov=nova --cov-fail-under=70`)
5. **Security** — `pip-audit` (dependencies), secret scan on the diff
6. **Build/package** — the artifact must build in CI, not just locally
7. **Deploy** (main only) — after tests pass on the merge commit

Fail fast: put the cheapest gates first so a broken PR fails in seconds, not minutes.

## CI Configuration (GitHub Actions)

```yaml
name: ci
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13", cache: pip }
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy nova/
      - run: pytest --cov=nova --cov-fail-under=70
      - run: pip-audit
```

- Cache dependencies; install with `--no-deps` after a locked install for speed if needed
- Use `pull_request` triggers for proposed changes; run the full suite on `push` to main
- Pin runner versions and actions by tag; never `@main` for third-party actions (supply-chain risk)

## Release Automation

1. **Semantic versioning** — `MAJOR.MINOR.PATCH`:
   - MAJOR: breaking changes
   - MINOR: new features, backward compatible
   - PATCH: bug fixes
2. **Changelog** — derive from conventional commits; group by `feat` / `fix` / `docs` / `chore`
3. **Tag & release notes** — `git tag v1.2.0 && git push --tags`; generate notes from the changelog
4. **Publish** — the release artifact must be reproducible from the tag, not from a local checkout

```bash
# bump
git checkout main && git pull --rebase
# update version, changelog (docs/RELEASE-NNN-*.md or CHANGELOG.md)
git add . && git commit -m "chore: release v1.2.0"
git tag v1.2.0 && git push && git push --tags
```

## Rollback

- Every deploy must have a rollback story: revert commit, redeploy previous artifact, or feature flag
- Keep the last N release artifacts — never depend on rebuilding an old tag from scratch
- Rollback is a release process, not a git ceremony — follow the runbook (see the operations skill)

## Pitfalls

- Don't let CI be green while local is red — same commands, same Python version, same deps
- Don't skip the coverage gate to merge quickly — the debt compounds
- Don't deploy from a feature branch on a whim — the pipeline is the only deploy path
- Don't bump versions by hand inconsistently — one source of truth (file, tag, and changelog must agree)
- Don't let a flaky test block everything — quarantine it with an issue and a ticket, don't delete it
