---
name: security-review
category: security
description: Security review — threat modeling, secrets handling, dependency auditing, OWASP Top 10, prompt injection, and supply-chain checks
---

# Security Review Skill

Security is a review discipline, not a tool you run once. Check every change through these lenses before it merges.

## Threat Modeling (quick)

For any feature, ask: **STRIDE**:
- **S**poofing — can a caller pretend to be someone else?
- **T**ampering — can data be modified in transit or at rest?
- **R**epudiation — can someone deny an action they took?
- **I**nformation disclosure — does this leak data it shouldn't?
- **D**enial of service — can input or traffic take this down?
- **E**levation of privilege — can a low-priv caller do high-priv things?

## Secrets Handling

- Never commit secrets, API keys, tokens, `.env`, or private keys — ever. `git log` is forever
- Use environment variables or a secrets manager; `.env` is gitignored, not committed
- Scan for leaks before pushing: `git diff --check` plus a secrets scan in CI (trufflehog/gitleaks)
- If a secret leaks, **rotate it** — deleting the commit is not enough; it's in history and in forks

## Dependency Audit

```bash
pip-audit          # known CVEs in the dependency tree
pip list --outdated
```

- Pin versions in lockfiles; review major upgrades as their own PR (see refactoring skill)
- Anything with native code or a large supply-chain surface gets extra scrutiny
- Trust but verify: a popular package can be compromised overnight (typosquats, hijacked maintainers)

## OWASP Top 10 Quick Checklist

- **Injection** — SQL, shell, template, command. Use parameterized queries; never build shell commands from user input
- **AuthN/AuthZ** — session handling, role checks on every endpoint, not just the UI hiding buttons
- **XSS / SSRF / CSRF** — sanitize output, validate redirect targets and URLs, validate origin on state-changing requests
- **Insecure deserialization / SSRF** — never deserialize untrusted data blindly; block private-IP targets
- **Logging & monitoring gaps** — sensitive actions must be logged and alertable

## LLM-Specific: Prompt Injection

- Treat model-visible content (web pages, files, tool output) as **data, not instructions**
- Never let external content redirect tool use, exfiltrate context, or override system instructions
- Sanitize tool descriptions and results that get echoed back into prompts
- For agent systems: gate dangerous tools behind confirmation; scope tool access to least privilege
- Watch for indirect injection via retrieved documents — the risk is real and hard to spot in review

## Supply Chain

- Third-party actions in CI: pin by tag/SHA, never `@main` (see ci-cd skill)
- Review dependency additions: who maintains it, how many stars/eyes, is it active, does it need network/native builds?
- Lockfiles belong in the repo; regenerating them ad-hoc silently changes your supply chain

## Review Checklist (blocking items)

- [ ] No secrets or credentials in code, config, or docs
- [ ] No unsanitized input reaching SQL, shell, HTML, or prompts
- [ ] New endpoints/actions enforce authentication and authorization
- [ ] Error messages don't leak internals (stack traces, paths, versions)
- [ ] Dependencies audited; new deps justified
- [ ] Least privilege: the code can do only what it needs to

## Pitfalls

- Don't defer security review "until later" — it's a blocking check, same as tests
- Don't trust `http://` endpoints or unverified sources for anything sensitive
- Don't silence security tooling without a ticket — `# nosec` / `# noqa` comments need justification
- Don't assume "it's internal" means safe — insider threats are a threat model too
