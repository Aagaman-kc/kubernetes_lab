# ☸️ Kubernetes Mastery Lab

> **From zero to production-grade Kubernetes — a hands-on, project-based bootcamp.**
>
> One system evolves through every phase: React → Node API → Postgres → AWS EKS,
> progressively layered with Deployments, Services, Ingress, CI/CD, HPA, monitoring, and RBAC.

![Status](https://img.shields.io/badge/status-in%20progress-yellow)
![Kubernetes](https://img.shields.io/badge/tools-Kubernetes-326CE5?logo=kubernetes)
![Docker](https://img.shields.io/badge/tools-Docker-2496ED?logo=docker)
![AWS](https://img.shields.io/badge/cloud-AWS%20EKS-FF9900?logo=amazon-aws)
![GitHub Actions](https://img.shields.io/badge/CI-CD-2088FF?logo=github-actions)
![Prometheus](https://img.shields.io/badge/monitoring-Prometheus%20%2B%20Grafana-E6522C?logo=prometheus)

---

## 🧭 Architecture — Final Target

```
         User
           |
        Ingress                          🌐 Single entry point
           |                            (path-based routing)
       ┌───┴───┐
       │       │
   React UI   /api ───→ Node API ──→ Postgres (PVC)
   (port 80)              │                  │
                          │            🗄️ StatefulSet
                    Load Generator           + Persistent Volume
                    (traffic simulation)
```

**What this system demonstrates:**
| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React (Container) | SPA served from k8s |
| Backend | Node.js API | Business logic & API layer |
| Database | PostgreSQL | Stateful storage with PV/PVC |
| Traffic | Python Load Generator | Simulates real user load |
| Routing | NGINX Ingress | Path-based L7 routing |
| Scaling | HPA + Metrics Server | Auto-scale under load |
| CI/CD | GitHub Actions | Build → Push → Deploy on push |
| Monitoring | Prometheus + Grafana | Metrics collection & dashboards |
| Security | RBAC | Namespace-scoped access control |
| Cloud | AWS EKS | Managed production cluster |

---

## ✅ Progress Tracker

| # | Phase | Status | What I Built | Key Skills |
|---|-------|--------|-------------|------------|
| 1 | [Installation + Cluster Setup](01.Installation/note.md) | ✅ Complete | Kind cluster with control-plane + worker | `kubectl`, `kind`, cluster architecture |
| 2 | [Pods, Namespaces, Labels & YAML](02.pods%2Cnamespace%2Clabels%2Cyamlbasic/note.md) | ✅ Complete | Multi-container pod with sidecar in `dev` namespace | YAML manifests, `kubectl logs/describe`, labels |
| 3 | [Deployments & Self-Healing](03.Deployment,replicas,self-healing,selector&template/note.md) | ✅ Complete | ReplicaSet, self-healing, scaling to 5 replicas, selector & template | Desired state, `kubectl scale`, rollout commands |
| 4 | **Services (ClusterIP)** | ⬜ Up next | Stable Service endpoint for Node API | Service discovery, pod-to-pod networking |
| 5 | **React + Node Integration** | ⬜ Up next | Full-stack: React → Node API inside cluster | Multi-service deployment |
| 6 | **K8s Networking Deep Dive** | ⬜ Up next | DNS, CoreDNS, service discovery experiments | `nslookup`, DNS resolution |
| 7 | **Postgres + StatefulSet + PVC** | ⬜ Up next | Database with persistent storage, survives restarts | PV/PVC, StatefulSet, storage lifecycle |
| 8 | **ConfigMaps & Secrets** | ⬜ Up next | DB credentials in Secrets, env config in ConfigMaps | Config injection, `Secrets` vs `ConfigMap` |
| 9 | **Load Generator** | ⬜ Up next | Python traffic simulator hitting Node API | Traffic simulation, observability prep |
| 9b | **Specialized Workloads** | ⬜ Up next | Job, CronJob, DaemonSet | One-shot, scheduled, per-node workloads |
| 10 | **GitHub Actions CI/CD** | ⬜ Up next | Build → Push → Deploy pipeline | Docker build, automated k8s deploy |
| 11 | **HPA (Horizontal Pod Autoscaler)** | ⬜ Up next | CPU-based auto-scaling with load generator | Metrics Server, scale-up/down policies |
| 12 | **Ingress + GatewayAPI** | ⬜ Up next | Path-based routing: `/` → React, `/api` → Node | L7 routing, Ingress Controller |
| 13 | **AWS EKS** | ⬜ Up next | Full stack on managed EKS cluster | Cloud K8s, LoadBalancer, node groups |
| 14 | **Security (RBAC)** | ⬜ Up next | Read-only user, namespace-scoped permissions | Roles, RoleBindings, ServiceAccounts |
| 15 | **Observability** | ⬜ Up next | Prometheus + Grafana dashboards | Metrics collection, latency/CPU/request dashboards |

---

## 🧠 Completed Phases — Detail

### Phase 1: Installation + Cluster Setup

**Goal:** Understand cluster architecture and set up the local toolchain.

| Skill | Detail |
|-------|--------|
| Cluster architecture | Control-plane (API server, scheduler, etcd) vs worker nodes |
| `kubectl` | CLI client for the K8s API server |
| `kind` | Kubernetes-in-Docker for local development |
| Multi-node cluster | Created a `control-plane + worker` kind cluster using config |

**Commands mastered:**
```bash
kind create cluster --name k8-lab --config multi-node-config.yaml
kubectl get nodes
kubectl cluster-info
kubectl config use-context kind-k8-lab
```

**Troubleshooting:** Diagnosed Docker connectivity, port conflicts, and context mismatches.

---

### Phase 2: Pods, Namespaces, Labels & YAML

**Goal:** Deploy a real application as a Pod and master the declarative YAML model.

**Manifest:** [`node.yaml`](02.pods,namespace,labels,yamlbasic/node.yaml) — multi-container Pod with `node-api` (Node.js) + `logger` (BusyBox sidecar).

| Concept | Implementation |
|---------|---------------|
| Pod | Smallest deployable unit wrapping 2 containers |
| Namespace | `dev` — logical cluster partitioning for isolation |
| Labels | `app: node-api`, `env: development` for filtering & selection |
| Declarative YAML | `apiVersion` / `kind` / `metadata` / `spec` pattern |

**Debugging skills:**
```bash
kubectl logs node-api -n dev -c logger   # Sidecar logs
kubectl describe pod node-api -n dev     # Events & status
kubectl get pods -n dev --show-labels    # Label-based filtering
```

**The mindset shift:** "I run containers" → "I declare desired state, and Kubernetes makes it happen."

---

### Phase 3: Deployments, Replicas & Self-Healing

**Goal:** Move from single Pods to production-grade Deployments with desired-state management.

**Manifest:** [`deployment.YAML`](03.Deployment,replicas,self-healing,selector&template/deployment.YAML) — Deployment with 3 nginx replicas.

| Concept | Implementation |
|---------|---------------|
| Deployment | Declarative controller managing ReplicaSets & Pods |
| Replicas | `spec.replicas: 3` — controller ensures exactly 3 pods running |
| Selector | `matchLabels: app: node-api` — links Deployment to its pods |
| Template | Pod blueprint embedded in `spec.template` |
| Self-Healing | Deleting a pod → ReplicaSet creates replacement immediately |
| Scaling | `kubectl scale deployment --replicas=5` grows from 3 → 5 |

**Debugging skills:**
```bash
kubectl delete pod <name> -n dev                     # Trigger self-healing
kubectl scale deployment node-api-deployment --replicas=5 -n dev  # Scale
kubectl get replicasets -n dev                        # Verify ReplicaSet
kubectl rollout status deployment/node-api-deployment -n dev      # Rollout check
```

**Troubleshooting learned:** YAML strictness — `apiVersion: apps/v1` (not `app/v1`), `spec.template` (not `templates`), `containers` (not `container`), RFC 1123 lowercase naming.

---

## 🧱 Repository Structure

```
kubernetes-lab/
├── README.md                          ← You are here
├── roadmap.ipynb                      ← Full 3-day learning plan
├── 01.Installation/
│   ├── note.md                        ← Phase notes & commands
│   └── note.ipynb
├── 02.pods,namespace,labels,yamlbasic/
│   ├── node.yaml                      ← Multi-container Pod manifest
│   ├── note.md
│   └── note.ipynb
├── 03.Deployment,replicas,self-healing,selector&template/
│   ├── deployment.YAML               ← Deployment manifest
│   ├── note.md                       ← Phase notes & commands
│   └── note.ipynb
├── 04.services/                       ← 🔜 Phase 4
├── ... (phases 5–15)
└── capstone/                          ← 🏆 Final production deployment
```

Each phase follows: **learn → build → document** with a manifest file (`.yaml`) and a note (`.md`).

---

## 🛠️ Technologies Used

| Category | Tools |
|----------|-------|
| **Container Orchestration** | Kubernetes, kind, kubectl, k9s |
| **Containers** | Docker, containerd |
| **Languages** | Node.js, Python, Bash, YAML |
| **CI/CD** | GitHub Actions |
| **Cloud** | AWS EKS |
| **Monitoring** | Prometheus, Grafana |
| **Frontend** | React |
| **Database** | PostgreSQL |
| **Security** | RBAC, Secrets |

---

## 🎯 Key Kubernetes Concepts Mastered So Far

- ✅ Cluster architecture: control-plane vs worker nodes
- ✅ Declarative YAML manifests (`apiVersion`, `kind`, `metadata`, `spec`)
- ✅ Pods — multi-container pods with sidecar pattern
- ✅ Namespaces — logical isolation within a cluster
- ✅ Labels & label selectors — filtering and automation
- ✅ `kubectl` — full CLI workflow: `apply`, `get`, `describe`, `logs`, `delete`
- ✅ Container debugging: `CrashLoopBackOff`, log streaming, event inspection
- ✅ Deployments — replicas, self-healing via ReplicaSet controller
- ✅ Selector + Template — linking Deployment → ReplicaSet → Pods
- ✅ Scaling — `kubectl scale` for horizontal pod scaling
- ✅ Rollout commands — `rollout status`, `rollout history`

---

## 🏁 The End Goal

By completing this bootcamp, I will have deployed a **full production microservices platform** on AWS EKS with:

- **Auto-scaling** under real traffic (HPA + Load Generator)
- **CI/CD pipeline** that rebuilds and redeploys on git push
- **Database persistence** that survives pod restarts (PVC)
- **Path-based routing** through a single Ingress endpoint
- **Monitoring** with dashboards for latency, CPU, and request rate
- **Security** with namespace-scoped RBAC

---

*Planned and tracked in [`roadmap.ipynb`](roadmap.ipynb) — a detailed 3-day intensive bootcamp blueprint.*
