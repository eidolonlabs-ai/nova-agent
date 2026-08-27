---
name: operations
category: devops
description: Production operations — monitoring, logging, incident response, on-call, postmortems, and deployment/rollback runbooks
---

# Operations Skill

Production is where code meets reality. Operate it with runbooks, not improvisation.

## Observability First

- **Logs** — structured, with correlation IDs (request/task/session). Log decisions and errors, not every heartbeat
- **Metrics** — the 4 golden signals: latency, traffic, errors, saturation
- **Health checks** — `/healthz` for liveness, `/readyz` for readiness; distinguish them
- **Alerts** — alert on symptoms users feel, not on every metric twitch. Every alert needs a runbook link

## Incident Response

1. **Acknowledge** — own it: "we are investigating" beats silence
2. **Assess** — severity (user impact × scope), who's affected, what changed recently
3. **Mitigate** — restore service first: rollback, flag off, scale up. Investigate *after* users are unblocked
4. **Communicate** — status updates on a cadence (every 15–30 min), even when there's nothing new
5. **Postmortem** — after resolution, not instead of it

## Postmortem Template

```markdown
## Incident: <short name>
**Date / duration / severity:**
**Impact:** who, what, how bad
**Timeline:** every action with timestamps (no blame, just facts)
**Root cause:** the actual trigger (ask "why" 5 times)
**Contributing factors:** what made it worse
**Action items:**
- [ ] code fix (owner, ticket)
- [ ] test/regression (owner, ticket)
- [ ] process/runbook improvement (owner, ticket)
```

Blameless by default: the system failed, not the person. The postmortem's job is preventing recurrence.

## Runbooks

- Every operational action that is not "click this once" gets a runbook: deploy, rollback, restart, restore backup, rotate secrets
- Runbooks live in the repo (`docs/RUN-NNN-*.md`) so they're versioned and reviewed
- A runbook must be executable by someone who has never seen the system before
- Test runbooks during calm times — a rollback runbook that doesn't work is a trap

## Deploy & Rollback Discipline

- Deploys are small, frequent, and reversible — never a big-bang Friday afternoon release
- Pin artifact versions; the deploy record says *what* went where and *when*
- Rollback = revert to the previous artifact per the runbook; verify health after, don't assume
- Feature flags let you disable a change without redeploying — prefer flags for risky behavior

## Pitfalls

- Don't alert on everything — alert fatigue is how real incidents go unnoticed
- Don't treat the postmortem as paperwork — action items with owners or it never happened
- Don't SSH into prod to "fix things quickly" — changes belong in the pipeline (see ci-cd skill)
- Don't let runbooks rot — review them whenever the system changes
- Don't store secrets in config files or env docs — use a secrets manager, rotated regularly
