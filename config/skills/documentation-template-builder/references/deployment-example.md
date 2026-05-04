# Rich Example: Deployment Guide (RUN doc)

> Illustrative RUN doc in ai-companions style using Fly.io. Adapt commands for your platform (Kubernetes, AWS, Heroku, etc.).

---

# RUN: Deploy Backend to Production (Fly.io)

**Last Updated:** May 2026  
**Type:** RUN (Operational Procedure)  
**Audience:** DevOps, Release Manager  
**Related:** [ADR-012](../adr/ADR-012-CLOUD_DEPLOYMENT_STORAGE.md), [Database Migrations](SPEC-060-DATABASE_MIGRATIONS.md)

---

## Prerequisites Checklist

- [ ] All tests passing locally (`pytest`)
- [ ] Code reviewed and approved
- [ ] Database backup scheduled
- [ ] Slack notifications enabled
- [ ] Rollback plan confirmed
- [ ] Team notified (if breaking changes)

## Quick Steps (Experienced)

```bash
# 1. Ensure clean state
git status && git pull origin main && poetry install

# 2. Run tests
pytest

# 3. Deploy
fly deploy -a ai-companions-prod

# 4. Migrate if needed
fly ssh console -a ai-companions-prod -C "alembic upgrade head"

# 5. Verify
curl https://api.ai-companions.com/health
```

## Detailed Walkthrough

### Phase 1: Pre-Deployment (30 min before)

**1.1 Verify test suite**
```bash
cd backend
poetry install
pytest -v --cov=app
# All tests must pass
```

**1.2 Check Fly.io status**
```bash
fly status -a ai-companions-prod
# Should show: "Running"
```

**1.3 Announce in Slack**
```
@team Deploying backend to production in 10 minutes.
Changes: [link to PR or commit]
```

### Phase 2: Database Migrations (if needed)

**2.1 Create migration**
```bash
cd backend
alembic revision --autogenerate -m "Describe change"
# Review generated file in alembic/versions/
```

**2.2 Test migration locally**
```bash
docker-compose up -d
docker exec -it ai-companions-backend-1 alembic upgrade head
docker exec -it ai-companions-backend-1 alembic current
```

**2.3 Commit migration**
```bash
git add backend/alembic/versions/
git commit -m "add migration: describe change"
git push origin feature-branch
```

### Phase 3: Deploy Backend

**3.1 Build and deploy**
```bash
fly deploy -a ai-companions-prod --remote-only
# Takes ~5 min
# Watch output for: "App deployed successfully"
```

**3.2 Run migrations**
```bash
fly ssh console -a ai-companions-prod
alembic upgrade head
alembic current
# Output should show migration head with (head) marker
exit
```

**3.3 Verify deployment**
```bash
# Health check
curl -s https://api.ai-companions.com/health | jq .

# Sample API call
curl -s https://api.ai-companions.com/chats | jq '.[] | .id' | head -5
```

### Phase 4: Verification & Monitoring (10 min)

**4.1 Check logs**
```bash
fly logs -a ai-companions-prod --lines 50
# Should show: No ERROR lines in last 50 logs
```

**4.2 Monitor metrics**
- CPU: Should stay <70% ([Grafana](https://grafana.internal/d/backend-prod))
- Memory: Should stay <80%
- Errors: Should be 0–2 per minute (not 50+)

**4.3 Announce success**
```
✅ Backend deployed to production.
Version: [commit hash]
Changes: [link to PR]
```

## Rollback Procedure

```bash
# 1. Immediate rollback
fly cancel-deployment -a ai-companions-prod
# OR
fly deploy -a ai-companions-prod --image <previous-image-hash>

# 2. If database migration broke
fly ssh console -a ai-companions-prod -C "alembic downgrade -1"

# 3. Verify
curl https://api.ai-companions.com/health

# 4. Announce
# @team Rolled back deployment. Investigating issue.
```

## Troubleshooting

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Deploy hangs | `fly status -a ai-companions-prod` | Cancel: `fly cancel-deployment` |
| Health check fails | `fly logs -a ai-companions-prod` | Migration issue; run `alembic downgrade -1` |
| High error rate | Check Sentry alerts | Rollback deployment; open incident |
| Database timeout | `alembic current` to check state | Manually fix or rollback |

## Post-Deployment (Optional)

- [ ] Run smoke tests against production
- [ ] Monitor Grafana dashboard for 1 hour
- [ ] Notify customer success of new features

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Database Migrations](SPEC-060-DATABASE_MIGRATIONS.md) | How migrations work, troubleshooting |
| [ADR-012](../adr/ADR-012-CLOUD_DEPLOYMENT_STORAGE.md) | Deployment architecture decisions |
| [Frontend Deployment](FRONTEND_FLY_DEPLOYMENT.md) | Web UI deployment steps |
| [Operational Guide](GUIDE-NNN-OPERATIONS.md) | Day-to-day operations and incident response |
