# Phase 4 — Services (ClusterIP)

## Problem: Ephemeral Pod IPs

Pods are created and destroyed constantly. Each gets a temporary IP:

```
Pod A → 10.244.0.5
Pod B → 10.244.0.6
Pod C → 10.244.0.7
```

If Pod A crashes, Kubernetes creates Pod D at `10.244.0.15`. Any client hardcoding Pod A's IP breaks. Direct Pod communication is unreliable.

## Solution: Service

A Service provides a **stable IP** and **DNS name** that front-ends a set of Pods. Clients talk to the Service, never directly to Pods.

```
Client → Service (stable) → Pod A / Pod B / Pod C
```

## Manifests

### `deployment.YAML`

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

### `service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: node-service
  namespace: dev
spec:
  selector:
    app: node-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
```

## Concepts Learned

| Concept | Key Insight |
|---|---|
| **Service** | Stable network endpoint for a set of Pods |
| **ClusterIP** | Default type — only accessible inside the cluster |
| **Selector** | `selector.app: node-api` finds all Pods with that label |
| **Endpoints** | Service maintains a live list of Pod IPs matching the selector |
| **DNS Name** | `node-service.dev.svc.cluster.local` — works even if Pods change |
| **Load Balancing** | Service distributes traffic across matching Pods |
| **kube-proxy** | Node component that implements Service traffic forwarding |

## Service Architecture

```
Deployment
    ↓
ReplicaSet
    ↓
Pod A ← labels: app=node-api
Pod B ← labels: app=node-api
Pod C ← labels: app=node-api
    ↑
  Service (selector: app=node-api)
```

- **Deployment** solves: How many Pods should exist?
- **Service** solves: How do I reliably reach those Pods?

## Challenge Completed

```bash
kind create cluster --name k8-lab
kubectl create namespace dev
kubectl apply -f deployment.YAML
kubectl apply -f service.yaml
kubectl get pods -n dev
kubectl get svc -n dev
kubectl describe svc node-service -n dev
kubectl scale deployment node-api-deployment --replicas=5 -n dev
kubectl describe svc node-service -n dev    # endpoints update automatically
kubectl run -it --rm debug --image=busybox --restart=Never -n dev -- sh
wget -qO- http://node-service              # hits nginx via Service
wget -qO- http://node-service.dev.svc.cluster.local  # FQDN also works
```

## Key Commands

| Command | What it does |
|---|---|
| `kubectl apply -f service.yaml` | Create/update Service from YAML |
| `kubectl get svc -n <ns>` | List Services with ClusterIP |
| `kubectl describe svc <name> -n <ns>` | See selector, endpoints, ports |
| `kubectl get endpoints <name> -n <ns>` | See live Pod IPs backing the Service |
| `kubectl scale deployment <name> --replicas=N -n <ns>` | Scale pods — endpoints auto-update |

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `a lowercase RFC 1123 label must consist of...` | Service name has uppercase | Use `node-service` (all lowercase) |
| `wget: bad address 'node-api-service'` | DNS name doesn't match Service name | Use `node-service` (matches `metadata.name`) |

## Next Up — Phase 5: React + Node Integration

- Full-stack deployment: React frontend → Node API Service
- Multi-service architecture with pod-to-pod communication
- DNS-based service discovery in practice
