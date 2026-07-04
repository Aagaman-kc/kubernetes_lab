# ☸️ Kubernetes Mastery Lab

> **From zero to production-grade Kubernetes — a hands-on, project-based bootcamp.**
>
> One system evolves through every phase: React → Node API → Postgres → AWS EKS,
> progressively layered with Deployments, Services, Ingress, CI/CD, HPA, monitoring, and RBAC.

![Status](https://img.shields.io/badge/status-9%20of%2010%20phases%20complete-blue)
![Kubernetes](https://img.shields.io/badge/tools-Kubernetes-326CE5?logo=kubernetes)
![Docker](https://img.shields.io/badge/tools-Docker-2496ED?logo=docker)
![AWS](https://img.shields.io/badge/cloud-AWS%20EKS-FF9900?logo=amazon-aws)
![GitHub Actions](https://img.shields.io/badge/CI-CD-2088FF?logo=github-actions)
![Prometheus](https://img.shields.io/badge/monitoring-Prometheus%20%2B%20Grafana-E6522C?logo=prometheus)

---

## 🧭 Architecture — Final Target

```
         User (port 30080)
            |
            ▼
    ┌──────────────┐
    │ NGINX Ingress │  path-based routing
    │ (NodePort)    │  /  → frontend-service:80
    └──────┬───────┘  /api → backend-service:80
           │
      ┌────┴────┐
      │         │
      ▼         ▼
 FastAPI UI   /api ──→ FastAPI API ──→ Postgres (PVC)
 (httpx)       │         │                  │
               │    Backend Pods ×2    🗄️ StatefulSet
               │                           + PVC (1Gi)
               │
          ─ ─ ─┴─ CI/CD ─ ─ ─
          Git push → GitHub Actions
          → build → push → deploy
```

**What this system demonstrates:**
| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | FastAPI (Python) | SPA served from k8s, proxies `/api` via httpx |
| Backend | FastAPI + psycopg2 | Business logic & PostgreSQL queries |
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
|---|---|---|---|---|
| 1 | [Cluster Setup & Architecture](01.Installation/note.md) | ✅ Complete | Kind cluster with control-plane + worker | `kubectl`, `kind`, cluster architecture |
| 2 | [Pods, Namespaces & Labels](02.pods%2Cnamespace%2Clabels%2Cyamlbasic/note.md) | ✅ Complete | Multi-container pod with sidecar in `dev` namespace | YAML manifests, `kubectl logs/describe`, labels |
| 3 | [Deployments & ReplicaSets](03.Deployment,replicas,self-healing,selector&template/note.md) | ✅ Complete | ReplicaSet, self-healing, scaling to 5 replicas | Desired state, `kubectl scale`, rollout commands |
| 4 | [Services (ClusterIP)](04.service/note.md) | ✅ Complete | Stable ClusterIP Service for nginx Deployment | Service discovery, pod-to-pod networking, load balancing |
| 5 | [Frontend + Backend Microservices](05.backend,frontend_website_using_k8/note.md) | ✅ Complete | Nginx frontend → FastAPI backend with proxy_pass | Multi-service deployment, Docker image build, kind load |
| 6 | [K8s Networking Deep Dive](06.Networking-deep-dive/note.md) | ✅ Complete | FastAPI frontend → backend via CoreDNS, DNS deep dive | Service discovery, CoreDNS, kube-proxy |
| 7 | [Stateful Applications & Configuration](07.pv%2Cconfigmap%2Csecrers/note.md) | ✅ Complete | PostgreSQL StatefulSet + PVC, ConfigMap + Secret injection, rolling update | PV/PVC, StatefulSet, Secrets, ConfigMap, rolling update |
| 8 | [**Autoscaling Under Load**](08.HPA%2Cmetrics-server%2Cloadgenerator/note.md) | ✅ Complete | Backend scaled 3→7 via HPA under load generator traffic | Metrics Server, HPA, traffic simulation |
| 9 | [**Ingress & CI/CD**](09.Ingress_cicd/note.md) | ✅ Complete | Path-based NGINX Ingress + GitHub Actions CI/CD pipeline | Ingress controller, path-based routing, CI/CD automation |
| 10 | **Production Readiness & Observability** | ⬜ Up next | RBAC, Prometheus, Grafana, EKS overview | Security, monitoring, cloud deployment |
| 🏆 | **Final Capstone** | ⬜ Up next | Full production stack on AWS EKS | Everything combined |

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

### Phase 4: Services (ClusterIP)

**Goal:** Provide a stable network endpoint for ephemeral Pods using a Service.

**Manifests:** [`deployment.YAML`](04.service/deployment.YAML) — 3 nginx replicas, [`service.yaml`](04.service/service.yaml) — ClusterIP Service.

| Concept | Implementation |
|---------|---------------|
| Service | Stable IP + DNS name fronting a set of Pods |
| ClusterIP | Default type — internal-only, accessible via `node-service` or FQDN |
| Selector | `selector: app: node-api` matches Pods by label |
| Endpoints | Auto-maintained list of Pod IPs; updates on scale/delete |
| Load Balancing | Traffic distributed across all matching Pods |

**Debugging skills:**
```bash
kubectl describe svc node-service -n dev        # Inspect selector & endpoints
kubectl get endpoints node-service -n dev        # Live Pod IPs
wget -qO- http://node-service                    # Test via Service DNS
kubectl scale deployment --replicas=5 -n dev     # Endpoints auto-expand
```

**Troubleshooting learned:** Service names must be lowercase RFC 1123; DNS name matches `metadata.name` (not the deployment name).

---

### Phase 5: Backend + Frontend Website Using K8s

**Goal:** Deploy a full-stack application — Nginx frontend talking to FastAPI backend inside the cluster.

**Manifests:** [`backend.yaml`](05.backend,frontend_website_using_k8/fastapi-backend/backend.yaml) — FastAPI Deployment + Service, [`frontend.yaml`](05.backend,frontend_website_using_k8/frontend/frontend.yaml) — Nginx Deployment + Service.

| Concept | Implementation |
|---------|---------------|
| Multi-Service Architecture | Frontend and backend as separate Deployments with separate Services |
| Nginx Reverse Proxy | `proxy_pass http://backend:80/;` forwards `/api` to backend Service |
| Service Discovery | Nginx uses `backend` hostname — K8s DNS resolves it automatically |
| Docker Image Build | Built images locally, loaded into kind with `kind load docker-image` |
| Field Name Matching | Frontend JS and backend JSON must use identical field names |

**Debugging skills:**
```bash
# Build and load images
docker build -t fastapi-backend:1.0 ./fastapi-backend
docker build -t frontend:1.0 ./frontend
kind load docker-image fastapi-backend:1.0 --name k8-lab
kind load docker-image frontend:1.0 --name k8-lab

# Apply and verify
kubectl apply -f fastapi-backend/backend.yaml
kubectl apply -f frontend/frontend.yaml
kubectl get pods -o wide
kubectl get svc

# Test connectivity
kubectl exec <frontend-pod> -- curl -s http://backend/
kubectl exec <frontend-pod> -- curl -s http://localhost/api

# Access in browser
kubectl port-forward service/frontend 8080:80
```

**Bugs fixed:** Missing `@` decorator in FastAPI route (returned 404), frontend/backend field name mismatch (`date` vs `time`).

---

### Phase 6: K8s Networking Deep Dive

**Goal:** Understand DNS-based service discovery and pod-to-pod communication inside the cluster.

**Manifests:** [`backend/backend.yaml`](06.Networking-deep-dive/backend/backend.yaml) — FastAPI backend Deployment + Service, [`frontend/frontend.yaml`](06.Networking-deep-dive/frontend/frontend.yaml) — FastAPI frontend Deployment + Service.

| Concept | Implementation |
|---------|---------------|
| CoreDNS | Internal DNS server resolving Service names to ClusterIPs |
| Service Discovery | Frontend calls `http://backend` — CoreDNS resolves it automatically |
| FQDN Pattern | `<service>.<namespace>.svc.cluster.local` |
| search Domains | `/etc/resolv.conf` in pods enables short name resolution (`backend` → FQDN) |
| Endpoints | Service auto-maintains live list of backing Pod IPs |
| kube-proxy | Forwards Service VIP traffic to individual Pod IPs |
| kind load docker-image | Required to make locally built images available in kind nodes |

**Debugging skills:**
```bash
# Deploy backend + frontend
docker build -t fastapi-backend:1.0 ./backend
docker build -t fastapi-frontend:1.0 ./frontend
kind load docker-image fastapi-backend:1.0 --name k8-lab
kind load docker-image fastapi-frontend:1.0 --name k8-lab
kubectl apply -f backend/backend.yaml
kubectl apply -f frontend/frontend.yaml

# DNS deep dive from inside the cluster
kubectl run net-debug --image=nicolaka/netshoot -it --rm --restart=Never -n dev -- /bin/bash
  curl http://backend                    # JSON response
  curl http://frontend                   # HTML with backend data
  nslookup backend                       # backend.dev.svc.cluster.local
  cat /etc/resolv.conf                   # search domains
  exit

# Access in browser
kubectl port-forward service/frontend 8080:80 -n dev
```

**Key insight:** A pod doesn't need to know *which* Pod IP it's talking to — it just uses the Service DNS name, and CoreDNS + kube-proxy handle the rest.

---

### Phase 7: PV/PVC, ConfigMap & Secrets

**Goal:** Deploy PostgreSQL with persistent storage, inject config via ConfigMaps + Secrets, and perform rolling updates.

**Manifests:** [`secrets.yaml`](07.pv,configmap,secrers/postgres/secrets.yaml) — Secret for DB credentials, [`pvc.yaml`](07.pv,configmap,secrers/postgres/pvc.yaml) — PersistentVolumeClaim, [`statefulset.yaml`](07.pv,configmap,secrers/postgres/statefulset.yaml) — PostgreSQL StatefulSet, [`service.yaml`](07.pv,configmap,secrers/postgres/service.yaml) — headless ClusterIP.

| Concept | Implementation |
|---------|---------------|
| Secret | Stores `POSTGRES_USER`/`POSTGRES_PASSWORD` — base64-encoded, never hardcoded |
| PVC | Requests 1Gi `ReadWriteOnce` storage — decouples storage from Pod lifecycle |
| StatefulSet | Stable Pod identity (`postgres-0`), ordered creation, `volumeClaimTemplates` for per-Pod PVC |
| Headless Service | `clusterIP: None` — direct Pod DNS: `postgres-0.postgres.dev.svc.cluster.local` |
| Config Injection | Backend reads `DB_HOST`, `DB_NAME` (ConfigMap) + `DB_USER`, `DB_PASSWORD` (Secret) via `os.getenv()` |
| Rolling Update | Changed backend image tag `1.0` → `1.1` — zero-downtime Pod replacement |
| Fake-Data Pattern | Started with hardcoded JSON → swapped to real Postgres queries without architecture changes |

**Debugging skills:**
```bash
# Deploy Postgres
kubectl apply -f secrets.yaml
kubectl apply -f pvc.yaml
kubectl apply -f statefulset.yaml
kubectl apply -f service.yaml

# Build & load backend v1.1 (with Postgres connection)
docker build -t backend-07:1.1 .
kind load docker-image backend-07:1.1 --name k8-lab

# Rolling update
kubectl apply -f backend.yaml
kubectl rollout status deployment/backend-deployment -n dev

# Verify
kubectl port-forward service/backend 8080:80 -n dev
# → {"users":[{"id":1,"name":"Alice"},...]}
```

**Common gotcha:** StatefulSet `volumes:` inside `spec.template.spec.containers` is invalid — persistent storage must go in `volumeClaimTemplates` at `spec` level.

---

### Phase 8: Autoscaling Under Load (HPA + Metrics Server)

**Goal:** Automatically scale backend Pods based on CPU load using HPA, Metrics Server, and a load generator.

**Manifests:** [`backend.yaml`](08.HPA,metrics-server,loadgenerator/backend/backend.yaml) — FastAPI backend with resource requests, [`hpa.yaml`](08.HPA,metrics-server,loadgenerator/backend/hpa.yaml) — HorizontalPodAutoscaler (min=3, max=10, target=60% CPU), [`load-generator.yaml`](08.HPA,metrics-server,loadgenerator/load_generator/load-generator.yaml) — Python traffic simulator.

| Concept | Implementation |
|---------|---------------|
| Metrics Server | Installed separately — collects per-Pod CPU/memory from kubelets |
| HPA | Reads metrics, computes desired replicas, updates Deployment |
| Formula | `desiredReplicas = ceil[currentReplicas × (currentMetric / targetMetric)]` |
| Resource Requests | HPA requires `resources.requests.cpu` on Pods to calculate utilization |
| Load Generator | 20 Python threads hitting backend in a loop to raise CPU |
| Scale Up | Instant — backend scaled from 3 → 5 → 7 replicas under load |
| Scale Down | Delayed — 5 min cooldown to prevent thrashing |
| kind TLS Fix | Metrics Server needs `--kubelet-insecure-tls` due to self-signed certs |

**Debugging skills:**
```bash
# Install Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Fix for kind self-signed certs
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Build images locally and load into kind
docker build -t backend:1.0 ./backend
kind load docker-image backend:1.0 --name k8
docker build -t load-generator:1.1 ./load_generator
kind load docker-image load-generator:1.1 --name k8

# Deploy and watch autoscaling
kubectl apply -f backend/backend.yaml
kubectl apply -f backend/hpa.yaml
kubectl apply -f load_generator/load-generator.yaml
kubectl get hpa -n dev -w                 # Watch replicas change
kubectl top pods -n dev                   # Real-time CPU per pod

# Stop load → scale down
kubectl delete deployment load-generator -n dev
```

**Common gotchas:** `ErrImagePull` when image isn't built/loaded into kind; `<unknown>` in HPA when Metrics Server is missing or hasn't started; empty `requirements.txt` causes `import requests` crash.

---

### Phase 9: Ingress Controller & CI/CD Pipeline

**Goal:** Expose frontend + backend through a single NGINX Ingress endpoint (path-based routing), then automate builds and deployments with a GitHub Actions CI/CD pipeline.

**Manifests:** [`ingress.yaml`](09.Ingress_cicd/k8s/ingress.yaml) — NGINX Ingress with path-based routing, [`config-and-secret.yaml`](09.Ingress_cicd/k8s/config-and-secret.yaml) — ConfigMap + Secret, [`postgres.yaml`](09.Ingress_cicd/k8s/postgres.yaml) — PostgreSQL StatefulSet, [`backend-deployment.yaml`](09.Ingress_cicd/k8s/backend-deployment.yaml) — Backend with env injection, [`frontend-deployment.yaml`](09.Ingress_cicd/k8s/frontend-deployment.yaml) — Frontend, [`deploy.yml`](09.Ingress_cicd/.github/workflows/deploy.yml) — CI/CD pipeline.

| Concept | Implementation |
|---------|---------------|
| Ingress | L7 routing — single `NodePort:30080` entry point with path-based dispatch |
| Ingress Controller | Installed separately in kind (`ingress-nginx`), maps host port 30080 → 80 |
| Path-Based Routing | `/` → frontend-service, `/api` → backend-service |
| No port-forward | Ingress exposes permanently — unlike earlier phases requiring `kubectl port-forward` |
| CI/CD Pipeline | GitHub Actions triggered on push to `main` with changes in `09.Ingress_cicd/` |
| Build & Push | Docker images built and pushed to Docker Hub tagged with commit SHA |
| Deploy Step | `azure/k8s-deploy` action updates deployments with new image tags |
| GitHub Secrets | `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `KUBECONFIG` injected at runtime |
| Secret Management | Kubeconfig base64-encoded and stored as GitHub secret |
| PostgreSQL Integration | Backend auto-creates `messages` table on startup, seeds initial data |
| FastAPI Frontend | Uses `httpx.AsyncClient` to proxy `/api` to backend — no nginx reverse proxy needed |
| Rolling Update | CI/CD pipeline triggers zero-downtime deployment with new image |

**Debugging skills:**
```bash
# Install Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

# Wait for controller
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# Build and load images locally
cd backend && docker build -t fastapi-backend:2.0 . && cd ..
cd frontend && docker build -t frontend:1.0 . && cd ..
kind load docker-image fastapi-backend:2.0 --name k8-lab
kind load docker-image frontend:1.0 --name k8-lab

# Apply all manifests
kubectl apply -f k8s/config-and-secret.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Test in browser (no port-forward needed!)
# http://localhost:30080/

# Check Ingress rules
kubectl get ingress -n production
kubectl describe ingress main-ingress -n production
```

**Bugs fixed:** Ingress controller must be installed for Kind (not automatic); Ingress must be in the same namespace as its backend Services; frontend must call the correct Service DNS name (`backend-service`); images must be loaded into kind before deployment.

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
├── 04.service/
│   ├── deployment.YAML                ← Deployment manifest (3 nginx replicas)
│   ├── service.yaml                   ← ClusterIP Service manifest
│   ├── note.md                        ← Phase notes & commands
│   └── note.ipynb
├── 05.backend,frontend_website_using_k8/
│   ├── fastapi-backend/
│   │   ├── main.py                    ← FastAPI backend application
│   │   ├── Dockerfile                 ← Backend container build
│   │   └── backend.yaml               ← Backend Deployment + Service
│   ├── frontend/
│   │   ├── index.html                 ← Frontend HTML with fetch to /api
│   │   ├── nginx.conf                 ← Nginx config with proxy_pass
│   │   ├── Dockerfile                 ← Frontend container build
│   │   └── frontend.yaml              ← Frontend Deployment + Service
│   ├── note.md                        ← Phase notes & commands
│   └── note.ipynb
├── 06.Networking-deep-dive/
│   ├── backend/
│   │   ├── app.py                     ← FastAPI backend (returns JSON)
│   │   ├── Dockerfile                 ← Backend container build
│   │   ├── requirements.txt
│   │   └── backend.yaml               ← Backend Deployment + Service
│   ├── frontend/
│   │   ├── main.py                    ← FastAPI frontend (calls backend via requests)
│   │   ├── Dockerfile                 ← Frontend container build
│   │   ├── requirements.txt
│   │   └── frontend.yaml              ← Frontend Deployment + Service
│   ├── note.md                        ← Phase notes & commands
│   └── note.ipynb
├── 07.pv,configmap,secrers/
│   ├── postgres/
│   │   ├── secrets.yaml               ← DB credentials Secret
│   │   ├── pvc.yaml                   ← PersistentVolumeClaim
│   │   ├── statefulset.yaml           ← PostgreSQL StatefulSet
│   │   └── service.yaml               ← Headless ClusterIP service
│   ├── backend/
│   │   ├── main.py                    ← FastAPI with Postgres connection
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── backend.yaml               ← Backend Deployment + Service
│   ├── frontend/
│   │   ├── main.py                    ← Frontend app
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── frontend.yaml              ← Frontend Deployment + Service
│   ├── note.md                        ← Phase notes & commands
│   └── note.ipynb
├── 08.HPA,metrics-server,loadgenerator/
│   ├── backend/
│   │   ├── main.py                    ← FastAPI backend
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── backend.yaml               ← Backend Deployment + Service (with CPU requests)
│   │   └── hpa.yaml                   ← HPA targeting 60% CPU, min=3 max=10
│   ├── frontend/
│   │   ├── main.py                    ← FastAPI frontend calling backend
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── frontend.yaml              ← Frontend Deployment + Service
│   ├── load_generator/
│   │   ├── main.py                    ← 20-thread traffic simulator
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── load-generator.yaml        ← Load Generator Deployment
│   ├── note.md                        ← Phase notes & commands
│   └── note.ipynb
├── 09.Ingress_cicd/
│   ├── k8s/
│   │   ├── config-and-secret.yaml     ← ConfigMap + Secret for DB config
│   │   ├── postgres.yaml              ← Headless Service + StatefulSet (1Gi PVC)
│   │   ├── backend-deployment.yaml    ← Deployment ×2 + ClusterIP Service
│   │   ├── frontend-deployment.yaml   ← Deployment ×1 + ClusterIP Service
│   │   └── ingress.yaml              ← NGINX Ingress (/ → frontend, /api → backend)
│   ├── backend/
│   │   ├── main.py                    ← FastAPI with psycopg2, auto-creates messages table
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── frontend/
│   │   ├── main.py                    ← FastAPI with httpx, serves HTML + proxies /api
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── .github/workflows/
│   │   └── deploy.yml                ← GitHub Actions: build → push → deploy on push
│   ├── note.md                        ← Phase notes & commands
│   └── note.ipynb
├── ... (phase 10)
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
- ✅ Services — ClusterIP for stable Pod networking
- ✅ Service discovery — DNS name + label selectors route traffic to Pods
- ✅ Load balancing — Service distributes across replicas automatically
- ✅ Multi-service architecture — Frontend + Backend as separate Deployments
- ✅ Nginx reverse proxy — `proxy_pass` for inter-service communication
- ✅ Docker image build & kind load — Local images loaded into kind cluster
- ✅ Full-stack K8s deployment — Browser → Frontend Service → Backend Service → Pods
- ✅ CoreDNS — Service name resolution inside the cluster
- ✅ DNS deep dive — FQDN pattern, search domains, `nslookup`, `/etc/resolv.conf`
- ✅ kubectl port-forward — Accessing ClusterIP Services from localhost
- ✅ PersistentVolumeClaim (PVC) — requesting storage decoupled from Pod lifecycle
- ✅ StatefulSet — stable Pod identity (`postgres-0`), ordered creation, `volumeClaimTemplates`
- ✅ Headless Service — `clusterIP: None` for direct Pod DNS
- ✅ Secret — base64-encoded sensitive data, injected via `secretKeyRef`
- ✅ ConfigMap — non-sensitive config injected as env vars
- ✅ Rolling update — zero-downtime Pod replacement by changing image tag
- ✅ HPA — horizontal autoscaling based on CPU utilization
- ✅ Metrics Server — cluster-wide resource metrics aggregation
- ✅ Load Generator — traffic simulation to trigger autoscaling
- ✅ kind + Metrics Server — `--kubelet-insecure-tls` workaround for self-signed certs
- ✅ Scale-up is instant, scale-down has a 5-min cooldown
- ✅ Ingress — L7 path-based routing with NGINX Ingress Controller
- ✅ Ingress Controller — installed separately for kind (ingress-nginx), NodePort 30080
- ✅ Path-based routing — `/` → frontend, `/api` → backend through single entry point
- ✅ No port-forward — Ingress exposes services permanently on host port 30080
- ✅ CI/CD pipeline — GitHub Actions triggered on git push to main
- ✅ Build & Push — Docker images built and pushed to Docker Hub tagged with commit SHA
- ✅ Automated deploy — `kubectl set image` triggered by CI/CD pipeline
- ✅ GitHub Secrets — `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `KUBECONFIG` injected at deploy-time
- ✅ FastAPI Frontend with httpx — async HTTP proxy to backend (no nginx reverse proxy needed)
- ✅ Full production stack — Browser → Ingress → Frontend → Backend → PostgreSQL

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
