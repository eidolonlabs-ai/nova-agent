# Rich Example: Operational Guide

> Illustrative operational guide in ai-companions style using Fly.io. Adapt commands for your platform.

---

# Operational Guide: AI Companions Backend

**Last Updated:** May 3, 2026  
**Type:** GUIDE (Operational)  
**On-call contact:** @backend-oncall (Slack)  
**Escalation policy:** 5 min to fix, then page; >30 min page manager  
**Related:** [Deployment Guide](DEPLOY_TO_FLY.md), [Architecture](ADR-010-SIMPLIFIED_STACK_ARCHITECTURE.md)

---

## Quick Reference

| Task | Command | Time |
|------|---------|------|
| Check prod status | `fly status -a ai-companions-prod` | 10s |
| View live logs | `fly logs -a ai-companions-prod --lines 100` | 5s |
| Check database | `fly postgres connect -a ai-companions-prod` | 20s |
| Restart backend | `fly restart -a ai-companions-prod` | 2 min |
| Check metrics | [Grafana Dashboard](https://grafana.internal/d/backend-prod) | 30s |

## Common Tasks

### 1. Check service health

```bash
curl -s https://api.ai-companions.com/health | jq .
# Expected: {"status":"ok","version":"v2.1.0","timestamp":"..."}
# If not 200, proceed to troubleshooting
```

### 2. View error logs

```bash
# Last 50 lines
fly logs -a ai-companions-prod --lines 50

# Filter for errors
fly logs -a ai-companions-prod --lines 500 | grep ERROR

# Follow in real-time (Ctrl+C to exit)
fly logs -a ai-companions-prod
```

### 3. Restart service (if hung)

```bash
fly restart -a ai-companions-prod
# Takes ~90 seconds

sleep 120
curl https://api.ai-companions.com/health
```

### 4. Check database connectivity

```bash
fly ssh console -a ai-companions-prod
psql $DATABASE_URL -c "SELECT 1;"
# If returns "1", DB is responding
exit
```

### 5. Emergency: Scale down then up

```bash
# Kill all instances
fly scale count 0 -a ai-companions-prod
sleep 30
fly scale count 2 -a ai-companions-prod
sleep 60
curl https://api.ai-companions.com/health
```

## Monitoring & Alerts

### Key Metrics

| Metric | Normal | Alert | Action |
|--------|--------|-------|--------|
| CPU | <50% | >80% for 5 min | Check top process; restart if needed |
| Memory | <60% | >85% for 5 min | Increase RAM tier or restart |
| Request latency | <200ms | >500ms p95 | Check slow queries; page DB team |
| Error rate | <0.1% | >1% | Page oncall immediately |
| DB connections | <20 | >50 | Check for connection leaks; restart |

### Alert Escalation

1. **⚠️ Warning (10 min to respond)**
   - CPU 70–80%, Error rate 0.5–1%
   - → Check logs, diagnose

2. **🔴 Critical (immediate response)**
   - CPU >85%, Error rate >2%, Database offline
   - → Page oncall

3. **🟠 Degraded (reduce load)**
   - Latency spiking, connection pool near limit
   - → Restart or scale up

## Troubleshooting

### Issue: "502 Bad Gateway"

```bash
fly status -a ai-companions-prod
curl https://api.ai-companions.com/health
fly logs -a ai-companions-prod --lines 50 | grep ERROR
```

| Cause | Check | Fix |
|-------|-------|-----|
| Backend down | Status showing "Running"? | `fly restart` |
| Database offline | `psql $DATABASE_URL -c "SELECT 1;"` | Page DB team |
| Out of memory | Grafana memory graph | `fly scale memory 2G` |

### Issue: "High error rate (>1% HTTP 500s)"

```bash
# 1. View errors
fly logs -a ai-companions-prod --lines 500 | grep ERROR | head -20

# 2. If database issue
fly ssh console -a ai-companions-prod -C \
  "psql \$DATABASE_URL -c 'SELECT count(*) FROM pg_stat_activity;'"

# 3. If timeout: increase query_timeout in config.yaml, then redeploy
fly deploy -a ai-companions-prod
```

### Issue: "Slow API responses (>500ms p95)"

```bash
fly ssh console -a ai-companions-prod
psql $DATABASE_URL -c \
  "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"
```

Fix options:
1. **Add index:** `CREATE INDEX idx_name ON table (column);`
2. **Optimize query:** Refactor to avoid full table scan
3. **Scale database:** Upgrade to bigger compute

## Escalation Tree

```
Issue detected
    ↓
Can you fix in <5 min? YES → Fix it, document in #incidents
    ↓ NO
Page @backend-oncall (Slack)
    ↓
Oncall can't fix in 10 min?
    ↓
Page @backend-manager + incident commander
```

## On-Call Shift Handoff

```bash
# 1. Check status
fly status -a ai-companions-prod

# 2. Review last 24h in #incidents Slack channel

# 3. Open Grafana: https://grafana.internal/d/backend-prod

# 4. Run health check
curl https://api.ai-companions.com/health

# 5. Post in #incidents: "✅ @backend-oncall handoff complete. All systems nominal."
```

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Deployment Guide](DEPLOY_TO_FLY.md) | How to deploy new versions |
| [Architecture](ADR-010-SIMPLIFIED_STACK_ARCHITECTURE.md) | System design overview |
| [Database Migrations](SPEC-060-DATABASE_MIGRATIONS.md) | Migration procedures |
