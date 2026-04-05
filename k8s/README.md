# Kubernetes Manifests for e-Agent-OS

## Prerequisites

- Kubernetes 1.28+
- nginx-ingress or traefik ingress controller
- metrics-server (for HPA)

## Quick Start

```bash
# 1. Apply namespace
kubectl apply -f namespace.yaml

# 2. Create secrets (edit secrets.yaml first!)
kubectl apply -f secrets.yaml

# 3. Build and push Docker image
docker build -t ghcr.io/andyzhengyan/enterprise-agent-employee:latest .
docker push ghcr.io/andyzhengyan/enterprise-agent-employee:latest

# 4. Apply all manifests
kubectl apply -f deployment.yaml
kubectl apply -f services.yaml
kubectl apply -f hpa.yaml
kubectl apply -f ingress.yaml

# 5. Check status
kubectl get pods -n e-agent-os
kubectl get svc -n e-agent-os
```

## Secrets Management

For production, use one of:
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) — encrypt secrets in git
- [External Secrets Operator](https://external-secrets.io/) — sync from AWS/GCP vault
- [Vault](https://www.vaultproject.io/) — Kubernetes auth

## Resource Tuning

Default resource requests/limits in `deployment.yaml`:
| Service | CPU (req/lim) | Memory (req/lim) |
|---------|---------------|-----------------|
| gateway | 100m / 500m | 128Mi / 512Mi |
| runtime | 250m / 1000m | 256Mi / 1Gi |
| model-hub | 100m / 500m | 128Mi / 512Mi |
| governance | 100m / 500m | 128Mi / 512Mi |
| config-center | 50m / 200m | 64Mi / 256Mi |
| redis | 50m / 200m | 64Mi / 256Mi |
