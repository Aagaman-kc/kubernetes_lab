# Phase 3 — Deployment, Replicas, Self-Healing, Selector & Template

## Challenge Completed

```
kind create cluster --name k8-lab              # Create cluster
kubectl create namespace dev                   # Isolate environment
kubectl apply -f deployment.YAML               # Deploy Deployment
kubectl get pods -n dev --show-labels          # Verify pods + labels
kubectl delete pod <name> -n dev               # Kill a pod → self-healing
kubectl scale deployment node-api-deployment --replicas=5 -n dev  # Scale up
kubectl get replicasets -n dev                 # See ReplicaSet managed by Deployment
kubectl rollout status deployment/node-api-deployment -n dev
kubectl rollout history deployment/node-api-deployment -n dev
```

## Deployment Manifest — `deployment.YAML`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: node-api-deployment
  namespace: dev
  labels:
    app: node-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: node-api
  template:
    metadata:
      labels:
        app: node-api
        tier: backend
    spec:
      containers:
        - name: node-api-deployment
          image: nginx
          ports:
            - containerPort: 80
```

## Concepts Learned

| Concept | Key Insight |
|---|---|
| **Deployment** | Declarative controller that manages ReplicaSets and Pods |
| **Replicas** | Desired number of pod copies; controller ensures target count |
| **Selector** | Links Deployment → ReplicaSet via `matchLabels` (must match pod template labels) |
| **Template** | Pod blueprint inside the Deployment spec |
| **Self-Healing** | Deleting a pod triggers immediate replacement — desired state is always enforced |
| **ReplicaSet** | Intermediate resource; Deployment creates & manages ReplicaSets, which create Pods |
| **Scaling** | `kubectl scale` or `spec.replicas` change — new pods are created instantly |
| **RollingUpdate** | Default strategy: 25% max unavailable, 25% max surge |

## Self-Healing Demo

```bash
# Delete a pod manually
kubectl delete pod node-api-deployment-5689667f65-nrv7x -n dev

# New pod appears automatically within seconds
kubectl get pods -n dev
# → new pod with different suffix created by ReplicaSet
```

## Scaling Demo

```bash
# Scale from 3 → 5 replicas
kubectl scale deployment node-api-deployment --replicas=5 -n dev

# Verify
kubectl get pods -n dev          # 5 pods running
kubectl get replicasets -n dev    # DESIRED=5, CURRENT=5, READY=5
```

## Troubleshooting Journey

| Error | Cause | Fix |
|---|---|---|
| `no matches for kind "Deployment" in version "app/v1"` | Typo: `app/v1` instead of `apps/v1` | Use `apiVersion: apps/v1` |
| `unknown field "spec.templates"` | Typo: `templates` instead of `template` | Use `spec.template` (singular) |
| `unknown field "spec.template.spec.container"` | Typo: `container` instead of `containers` | Use `containers` (plural) |
| `a lowercase RFC 1123 subdomain must consist of...` | Name contains uppercase letters | Use `node-api-deployment` (all lowercase) |

## Key Commands

| Command | What it does |
|---|---|
| `kubectl apply -f deployment.yaml` | Create/update resources from YAML |
| `kubectl get pods -n <ns> --show-labels` | List pods with labels |
| `kubectl delete pod <name> -n <ns>` | Delete pod (Deployment replaces it) |
| `kubectl scale deployment <name> --replicas=N -n <ns>` | Scale replicas |
| `kubectl get replicasets -n <ns>` | List ReplicaSets |
| `kubectl rollout status deployment/<name> -n <ns>` | Check rollout progress |
| `kubectl rollout history deployment/<name> -n <ns>` | View rollout revision history |

## Next Up — Phase 4: Services (ClusterIP)

Pods are ephemeral — they get IPs that change. **Services** provide a stable endpoint:
- ClusterIP for internal pod-to-pod communication
- Labels and selectors to route traffic to the right pods
- Load balancing across replicas
