# ☸️ Kubernetes Lab — My 3-Day Intensive Bootcamp

I built this repository to go from **zero to Kubernetes** in 3 days. Every phase follows the same pattern: learn → build → write notes.

> **Approach:** Project-based, no videos. I evolve ONE system (React → Node API → Postgres) step-by-step through Kubernetes concepts.

---

## 🗺️ Roadmap

I planned the full journey in [`roadmap.ipynb`](roadmap.ipynb). Below is my progress.

---

## ✅ Progress Tracker

### Day 1 — Kubernetes Core + Basic Deployment

| # | Phase | Status | Notes |
|---|-------|--------|-------|
| 1 | **Installation + Cluster Setup** | ✅ Done | [`note.md`](01.Installation/note.md) · [`note.ipynb`](01.Installation/note.ipynb) |
| 2 | **Pods, Namespaces, Labels & YAML** | ✅ Done | [`note.md`](02.pods,namespace,labels,yamlbasic/note.md) · [`note.ipynb`](02.pods,namespace,labels,yamlbasic/note.ipynb) |
| 3 | **Deployments (The Real K8s Unit)** | ⬜ Up next | |
| 4 | **Services (Networking Layer)** | ⬜ Up next | |
| 5 | **React + Node Integration** | ⬜ Up next | |

### Day 2 — Networking + Storage + Real Architecture

| # | Phase | Status | Notes |
|---|-------|--------|-------|
| 6 | **K8s Networking Deep Dive** | ⬜ Up next | |
| 7 | **Postgres + StatefulSet + PV/PVC** | ⬜ Up next | |
| 8 | **ConfigMaps + Secrets** | ⬜ Up next | |
| 9 | **Load Generator** | ⬜ Up next | |
| 9b | **Specialized Workloads (Job, CronJob, DaemonSet)** | ⬜ Up next | |

### Day 3 — Production Kubernetes + CI/CD + AWS

| # | Phase | Status | Notes |
|---|-------|--------|-------|
| 10 | **GitHub Actions CI/CD** | ⬜ Up next | |
| 11 | **HPA (Horizontal Pod Autoscaler)** | ⬜ Up next | |
| 12 | **Ingress + GatewayAPI** | ⬜ Up next | |
| 13 | **AWS EKS (Real Production K8s)** | ⬜ Up next | |
| 14 | **Security Basics (RBAC)** | ⬜ Up next | |
| 15 | **Observability (Prometheus + Grafana)** | ⬜ Up next | |

---

## 🧠 What I've Learned So Far

### Phase 1 — Installation

I installed `kubectl`, `kind`, and Docker, then created my first cluster with `kind create cluster`. I learned:

- A **cluster** has a control-plane + workers
- **Control-plane** runs the API server, scheduler, controller manager, and etcd
- **Workers** run my application pods
- `kubectl` is just an HTTP client for the API server
- Kind runs K8s inside Docker containers

### Phase 2 — Pods, Namespaces, Labels

I deployed a multi-container pod (`node-api` + `logger` sidecar) into a `dev` namespace. I learned:

- **Pod** = smallest deployable unit, wrapper around containers
- **Namespace** = logical cluster partitioning for isolation
- **Labels** = key-value tags for selection and automation
- **YAML** = declarative syntax: `apiVersion`, `kind`, `metadata`, `spec`
- Debugging with `kubectl logs`, `kubectl describe`, and multi-container `-c` flag

> **The big shift:** I stopped thinking "I run containers" and started thinking "I declare desired state, and Kubernetes makes it happen."

---

## 🚀 Next: Phase 3 — Deployments

Pods alone aren't used in production. Deployments give me:
- Replicas & scaling
- Self-healing (auto-restart on failure)
- Rolling updates & zero-downtime deployments
- Version upgrades & rollbacks

---

## 🧭 Final Goal

By the end of this bootcamp, I will have deployed this full system on AWS EKS:

```
        User
          |
       Ingress
          |
      React UI
          |
     Node API ───────→ Postgres (PVC)
          |
     Load Generator
```

With CI/CD, monitoring (Prometheus + Grafana), auto-scaling (HPA), and RBAC security.

---

*Inspired by the [roadmap.ipynb](roadmap.ipynb) — my full 3-day plan.*
