# Phase 2 — Pods, Namespaces, Labels & YAML Basics

## Challenge Completed

```
kind create cluster --name k8              # Create cluster
kubectl create namespace dev               # Isolate environment
kubectl apply -f node.yaml                 # Deploy pod declaratively
kubectl get pods -n dev                    # List pods in namespace
kubectl logs node-api -n dev -c logger     # Stream logs from sidecar
kind delete clusters --all                 # Teardown
```

## Pod Manifest — `node.yaml`

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: node-api
  namespace: dev
  labels:
    app: node-api
    env: development
spec:
  containers:
    - name: node-api
      image: node:22-alpine
      ports:
        - containerPort: 8080
    - name: logger
      image: busybox
      command:
        - sh
        - -c
        - |
          while true; do
            echo "Hello from Kubernetes $(date)"
            sleep 5
          done
```

- **Multi-container pod**: `node-api` (app) + `logger` (sidecar)
- **Namespace isolation**: pod lives in `dev`
- **Labels**: `app` and `env` for grouping/selection

## Concepts Learned

| Concept | Key Insight |
|---|---|
| **Pods** | Smallest deployable unit; wrapper around one or more containers |
| **Namespaces** | Logical cluster partitioning; not separate machines |
| **Labels** | Key-value tags for selection, filtering, and automation |
| **YAML** | Declarative syntax: `apiVersion`, `kind`, `metadata`, `spec` |
| **kind** | Kubernetes-in-Docker; cluster runs as containers |
| **containerd** | Container runtime *inside* the node, not Docker CLI |
| **kubectl** | Talks only to the API server, never directly to containers |

## Debugging Skills

- `kubectl logs <pod> -n <ns>` — view container output
- `kubectl logs <pod> -n <ns> -c <container>` — target a specific container in a multi-container pod
- `kubectl describe pod <pod> -n <ns>` — inspect events, status, conditions
- `CrashLoopBackOff` — container keeps crashing; check logs + describe

## The Mindset Shift

> **Before:** "I run containers"
>
> **After:** "I declare desired state, and Kubernetes makes it happen"

This is the fundamental paradigm of Kubernetes — declarative over imperative.

## Next Up — Phase 3: Deployments

Pods alone are not used in production. **Deployments** are the real unit:

- Replicas & scaling
- Self-healing (restart, reschedule)
- Rolling updates & rollbacks
- Zero-downtime deployments
- Version upgrades
