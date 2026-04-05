# Operations Runbook — e-Agent-OS

## Quick Reference

| Service | Port | Health Endpoint |
|---------|------|----------------|
| Gateway | 8000 | `GET /health` |
| Runtime | 8001 | `GET /health` |
| ModelHub | 8002 | `GET /model-hub/health` |
| Governance | 8007 | `GET /governance/health` |
| ConfigCenter | 8008 | `GET /config-center/health` |
| Redis | 6379 | `redis-cli ping` |

## Common Failure Scenarios

---

### 1. Gateway Returns 502 Bad Gateway

**Symptoms**: `curl http://localhost:8000/gateway/execute` returns 502.

**Diagnosis**:
```bash
# Check if Runtime is running
curl http://localhost:8001/health

# Check Runtime logs
kubectl logs -n e-agent-os deploy/runtime -f

# Check Runtime pod status
kubectl get pods -n e-agent-os -l app=runtime
```

**Resolution**:
```bash
# Restart Runtime pods
kubectl rollout restart deployment/runtime -n e-agent-os

# If OOM: increase memory limits in k8s/deployment.yaml
# If CrashLoopBackOff: check logs for Python exception
```

---

### 2. ModelHub Returns 503 Service Unavailable

**Symptoms**: Runtime tasks fail with `ModelHubError 3001`.

**Diagnosis**:
```bash
# Check ModelHub health
curl http://localhost:8002/model-hub/health

# Check sidecar process
nc -zv localhost 8090 2>&1

# Check if MINIMAX_API_KEY is set
echo $MINIMAX_API_KEY
```

**Resolution**:
```bash
# If sidecar down: restart pi-mono sidecar
# If no API key: set MINIMAX_API_KEY env var and restart ModelHub
kubectl set env deployment/model-hub MINIMAX_API_KEY=<key> -n e-agent-os
kubectl rollout restart deployment/model-hub -n e-agent-os

# If quota exceeded: wait for daily reset or upgrade plan
```

---

### 3. Runtime Task Hangs (No Response)

**Symptoms**: `execute` endpoint never returns, task stuck in PENDING.

**Diagnosis**:
```bash
# Check Runtime logs for last executed steps
kubectl logs -n e-agent-os deploy/runtime --tail=100 | grep -E "(step|execute|ERROR)"

# Check Redis connectivity
redis-cli -n 0 LLEN sessions

# Check if ModelHub is responding to completions
curl -X POST http://localhost:8002/model/chat -d '{"messages":[]}' --max-time 5
```

**Resolution**:
```bash
# Cancel the stuck task via Gateway
curl -X POST http://localhost:8000/gateway/tasks/{task_id}/cancel

# If Redis stuck: flush session queue (dev only!)
redis-cli -n 0 FLUSHDB

# Restart Runtime
kubectl rollout restart deployment/runtime -n e-agent-os
```

---

### 4. RBAC/ABAC Permission Denied (403)

**Symptoms**: Valid requests return 403 even with correct role.

**Diagnosis**:
```bash
# Check the JWT token is not expired
python3 -c "import jwt; import sys; print(jwt.decode(sys.argv[1], options={'verify_signature': False})['exp'])" <token>

# Check user's role in Governance
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:8007/governance/roles/{tenant_id}/{user_id}

# Check ABAC policy for the resource
curl http://localhost:8007/governance/policies
```

**Resolution**:
```bash
# Re-issue token with correct role
curl -X POST "http://localhost:8007/governance/token?user_id=alice&tenant_id=tenant-001&role=tenant_admin"

# Or assign role via Governance API
curl -X POST http://localhost:8007/governance/roles/assign \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"alice","role":"tenant_admin","tenant_id":"tenant-001"}'
```

---

### 5. Config Change Not Reflecting

**Symptoms**: Service still using old config value after update.

**Diagnosis**:
```bash
# Check if config was published (not just updated)
curl http://localhost:8008/config-center/configs/{namespace}/{key}
# Look for status: "published" (not "draft")

# Check subscriber registration
curl http://localhost:8008/config-center/subscribers

# Check push notification delivery in subscriber logs
```

**Resolution**:
```bash
# Publish the draft config
curl -X POST "http://localhost:8008/config-center/configs/{namespace}/{key}/publish" \
  -d "comment=activating config"

# Or manually trigger subscriber pull
# (Subscribers should implement pull-on-startup as fallback)
kubectl rollout restart deployment/runtime -n e-agent-os
```

---

### 6. Approval Request Stuck (Pending)

**Symptoms**: Approval request stuck in PENDING beyond SLA.

**Diagnosis**:
```bash
# List pending approvals
curl http://localhost:8007/governance/approvals/requests?status=pending

# Check approval workflow definition
curl http://localhost:8007/governance/approvals/workflows

# Get request details
curl http://localhost:8007/governance/approvals/requests/{request_id}
```

**Resolution**:
```bash
# Check timeout escalation (run check_timeouts)
curl -X POST http://localhost:8007/governance/approvals/check-timeouts
# This will escalate timed-out requests

# Manually approve/reject (platform_admin only)
curl -X POST http://localhost:8007/governance/approvals/decide \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "apr-xxx",
    "decision": "approved",
    "comment": "Manual override by admin",
    "approver_id": "platform_admin"
  }'
```

---

### 7. Redis Connection Refused

**Symptoms**: Services fail with `ConnectionError: Redis connection refused`.

**Diagnosis**:
```bash
# Check Redis pod
kubectl get pods -n e-agent-os -l app=redis

# Test Redis directly
kubectl exec -it -n e-agent-os deploy/redis -- redis-cli ping

# Check Redis logs
kubectl logs -n e-agent-os deploy/redis --tail=50
```

**Resolution**:
```bash
# If Redis OOM: increase memory limit or add eviction policy
# If Redis down: delete pod to force restart
kubectl delete pod -n e-agent-os -l app=redis

# If data loss acceptable (dev): redis-cli FLUSHDB
```

---

## Escalation Path

| Severity | Response Time | Contacts |
|----------|---------------|----------|
| P0 (service down) | 15 min | On-call SRE + Engineering Lead |
| P1 (degraded) | 1 hour | On-call SRE |
| P2 (non-critical) | 1 business day | Engineering team |

## Emergency Contacts

Replace with actual contacts:
- Engineering Lead: `<name> <email>`
- On-call SRE: PagerDuty (pagerduty.com/...)
- Security incidents: security@example.com
