# Service Level Objectives — e-Agent-OS

## Service Map

```
Client
  │
  ▼
Gateway (:8000) ──────► Runtime (:8001)
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                    │
    ModelHub           SkillHub              ConnectorHub
    (:8002)           (:8004)              (:8003)
         │                   │                    │
         └──────────────────►KnowledgeHub ◄───────┘
                              (:8005)
```

## Service Level Indicators (SLIs)

### Gateway

| Indicator | Target | Measurement |
|-----------|--------|-------------|
| Availability | 99.9% | `(total_minutes - downtime_minutes) / total_minutes` |
| P99 Latency (execute endpoint) | < 30s | Request duration at 99th percentile |
| Error Rate | < 1% | `5xx responses / total responses` |

### Runtime

| Indicator | Target | Measurement |
|-----------|--------|-------------|
| Availability | 99.5% | Health check uptime |
| P99 Latency (generate_plan) | < 10s | Planning phase duration |
| P99 Latency (execute_step) | < 30s | Step execution duration |
| Error Rate | < 2% | Task failures / total tasks |

### ModelHub

| Indicator | Target | Measurement |
|-----------|--------|-------------|
| Availability | 99.5% | Health check uptime |
| P99 Latency (chat completion) | < 5s | LLM response time |
| Fallback success rate | > 95% | Successful fallback / total fallbacks |
| Quota exhaustion rate | < 0.1% | Quota exceeded / total requests |

### Governance

| Indicator | Target | Measurement |
|-----------|--------|-------------|
| Availability | 99.9% | Health check uptime |
| P99 Latency (permission check) | < 50ms | Sync permission evaluation |
| Approval SLA | < 60min | Time from submission to approval |

### ConfigCenter

| Indicator | Target | Measurement |
|-----------|--------|-------------|
| Availability | 99.9% | Health check uptime |
| Push notification latency | < 2s | Config change → subscriber notified |
| Version history retention | 90 days | Config version snapshots |

## Error Budget

| Service | Monthly Error Budget (99.9%) | Monthly Error Budget (99.5%) |
|---------|----------------------------|----------------------------|
| Gateway | 43.8 min | 3.6 hours |
| Runtime | 43.8 min | 3.6 hours |
| ModelHub | 43.8 min | 3.6 hours |
| Governance | 43.8 min | — |

## Availability Targets by Tier

| Tier | Services | Target | Use Case |
|------|----------|--------|----------|
| Critical | Gateway, Runtime | 99.9% | Core execution path |
| Standard | ModelHub, Governance, ConfigCenter | 99.5% | Business logic |
| Best-effort | SkillHub, ConnectorHub, KnowledgeHub | 99% | Enrichment |

## Alert Thresholds

| Alert | Threshold | Severity | Window |
|-------|-----------|----------|--------|
| High Error Rate | > 1% 5xx on Gateway | P1 | 5 min |
| Latency Degradation | P99 > 30s on Runtime | P1 | 5 min |
| ModelHub Down | Unavailable > 1 min | P0 | 1 min |
| Quota Warning | > 80% of daily quota used | P2 | 10 min |
| Approval SLA Breach | Pending > 60 min | P2 | 1 min |

## SLO Review Cadence

- **Weekly**: Error budget burn rate review (P1 alerts auto-page)
- **Monthly**: SLO target review with stakeholders
- **Quarterly**: Error budget accounting and architectural review

## Definitions

- **P99 Latency**: 99th percentile of request durations
- **Error Rate**: Percentage of requests returning 5xx responses
- **Availability**: Uptime as percentage of total time
- **MTTR**: Mean Time To Recovery (from incident to service restoration)
- **Error Budget**: Allowable downtime/errors within SLO target
