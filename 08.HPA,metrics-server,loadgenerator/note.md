# 08: HPA, Metrics Server & Load Generator — Full Walkthrough

**Goal:** Auto-scale backend Pods based on CPU load — more traffic = more Pods, less traffic = fewer Pods.

**Stack:** Frontend (FastAPI) → calls Backend (FastAPI) → Load Generator (Python threads hitting backend)

---

## Architecture

```
Load Generator (20 threads)
         │
         │  HTTP GET /
         ▼
   ┌──────────────────┐
   │  coredns resolves │  http://backend → ClusterIP
   │  "backend"        │
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  backend Service  │  (ClusterIP, round-robin to backend Pods)
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────────────────────────────┐
   │  backend Pods × N (auto-scaled by HPA)  │
   │  CPU request: 100m, limit: 500m         │
   └──────────────────────────────────────────┘
            ▲
            │ reads CPU metrics
   ┌──────────────────┐
   │  Metrics Server   │  collects per-Pod CPU from kubelet
   └────────┬─────────┘
            │
            ▼
   ┌──────────────────┐
   │  HPA (backend-hpa)│  target: 60% CPU → desiredReplicas = ceil[current × (current / target)]
   └──────────────────┘
```

---

## Step 1 — Create Cluster

```bash
kind create cluster --name k8
kubectl create namespace dev
```

> ❌ **Mistake:** `kubectl get pods -n dev` was empty initially because kubectl was pointed at the **Docker Desktop** context, not the kind cluster.
> ```bash
> kubectl config use-context kind-k8   # ✅ Fix — switch to kind context
> ```

---

## Step 2 — Backend (Target for Autoscaling)

### `backend/main.py`

```python
from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def home():
    data = {
        "name":"aagaman.k.c",
        "message":"hello from phase 8"
    }
    return data
```

### `backend/requirements.txt`

```
fastapi
uvicorn[standard]
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]
```

### `backend/backend.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: backend
  namespace: dev
  labels:
    app: backend

spec:
  replicas: 3

  selector:
    matchLabels:
      app: backend

  template:
    metadata:
      labels:
        app: backend

    spec:
      containers:
      - name: backend
        image: backend:1.0

        ports:
        - containerPort: 80

        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"

          limits:
            cpu: "500m"
            memory: "256Mi"

---
apiVersion: v1
kind: Service

metadata:
  name: backend
  namespace: dev

spec:
  selector:
    app: backend

  ports:
  - port: 80
    targetPort: 80

  type: ClusterIP
```

> **Resource requests are REQUIRED for HPA.** Without `resources.requests.cpu`, the HPA cannot calculate CPU utilization percentages.

### Commands

```bash
cd .\08.HPA,metrics-server,loadgenerator\backend\
docker build -t backend:1.0 .
kind load docker-image backend:1.0 --name k8
kubectl apply -f .\backend.yaml

kubectl get pods -n dev
# 3/3 Running
```

---

## Step 3 — Frontend (Visual Feedback)

### `frontend/main.py`

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

@app.get('/',response_class=HTMLResponse)
def home():
    response = requests.get("http://backend")
    data = response.json
    return f"""
    <html>
    <head>
        <title>Kubernetes Demo</title>
    </head>

    <body style="font-family:Arial">

        <h1>Frontend Pod</h1>
        <h2>Response from Backend</h2>
        <pre>{data}</pre>

    </body>
    </html>
"""
```

### `frontend/requirements.txt`

```
uvicorn
fastapi
requests
```

### `frontend/Dockerfile`

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]
```

### `frontend/frontend.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: dev
  labels:
    app: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: frontend:1.0
        ports:
        - containerPort: 80

---
apiVersion: v1
kind: Service

metadata:
  name: frontend
  namespace: dev

spec:
  selector:
    app: frontend

  ports:
  - port: 80
    targetPort: 80

  type: ClusterIP
```

### Commands

```bash
cd .\08.HPA,metrics-server,loadgenerator\frontend\
docker build -t frontend:1.0 .
kind load docker-image frontend:1.0 --name k8
kubectl apply -f .\frontend.yaml

kubectl get pods -n dev
# 5 pods running (3 backend + 2 frontend)
```

---

## Step 4 — Metrics Server

**HPA cannot work without Metrics Server.** Metrics Server collects per-Pod CPU/memory from kubelets and exposes them via the Metrics API.

### Install

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Fix for kind (self-signed TLS certs)

Kind nodes use self-signed certificates. Metrics Server refuses to connect by default.

```bash
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

Verify it's running:

```bash
kubectl get pods -n kube-system | Select-String "metrics"
# metrics-server-xxxxxxxxxx-xxxxx   1/1   Running

kubectl top pods -n dev
# NAME                       CPU(cores)   MEMORY(bytes)
# backend-xxxxx-xxxxx        85m          34Mi
# backend-xxxxx-xxxxx        89m          34Mi
# ...
```

> ❌ **Before the fix:** HPA showed `cpu: <unknown>/60%` — no metrics available.
> ```bash
> # HPA events showed:
> # Warning  FailedGetResourceMetric  ... unable to fetch metrics from resource metrics API
> ```

---

## Step 5 — HPA Configuration

### `backend/hpa.yaml`

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: dev
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```

**How HPA calculates desired replicas:**

```
desiredReplicas = ceil[currentReplicas × (currentMetricValue / desiredMetricValue)]
```

Example: 3 Pods at 90% CPU with target 60%:
```
desiredReplicas = ceil[3 × (90 / 60)] = ceil[4.5] = 5
```

### Apply

```bash
kubectl apply -f .\hpa.yaml
kubectl get hpa -n dev
# NAME          REFERENCE          TARGETS              MINPODS   MAXPODS   REPLICAS
# backend-hpa   Deployment/backend   cpu: <unknown>/60%   3         10        3
```

> The `<unknown>` means Metrics Server isn't collecting yet (or just installed). Wait ~30s and it populates.

---

## Step 6 — Load Generator

The load generator is a Python script that spawns 20 threads hammering the backend with HTTP GET requests. This artificially raises CPU usage on the backend Pods, triggering the HPA.

### `load_generator/main.py`

```python
import threading
import requests

URL = "http://backend"


def generate_load():
    while True:
        try:
            requests.get(URL, timeout=2)
        except Exception:
            pass


# Start 20 worker threads
for _ in range(20):
    t = threading.Thread(target=generate_load)
    t.daemon = True
    t.start()

# Keep the main process alive
while True:
    pass
```

### `load_generator/requirements.txt`

```
requests
```

> ⚠️ **requirements.txt was empty initially** — the Dockerfile's `RUN pip install -r requirements.txt` installed nothing, and the Pod crashed on `import requests`. Had to add `requests` to the file.

### `load_generator/Dockerfile`

```dockerfile
FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY main.py .

CMD ["python", "main.py"]
```

### `load_generator/load-generator.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: load-generator
  namespace: dev

spec:
  replicas: 1

  selector:
    matchLabels:
      app: load-generator

  template:
    metadata:
      labels:
        app: load-generator

    spec:
      containers:
      - name: load-generator
        image: load-generator:1.1
```

> ❌ **ErrImagePull trap:** The YAML references `load-generator:1.1` but that image doesn't exist on Docker Hub. It must be:
> 1. Built locally: `docker build -t load-generator:1.1 .`
> 2. Loaded into kind: `kind load docker-image load-generator:1.1 --name k8`
>
> **Before fix:** Pod showed `ImagePullBackOff` trying to pull from `docker.io/library/load-generator:1.1` which doesn't exist.

### Commands

```bash
cd .\08.HPA,metrics-server,loadgenerator\load_generator\
docker build -t load-generator:1.1 .
kind load docker-image load-generator:1.1 --name k8
kubectl apply -f .\load-generator.yaml

kubectl get pods -n dev
# load-generator-xxxxx   1/1   Running
```

---

## Step 7 — Watch Autoscaling in Action

### Before load (no Metrics Server — broken)

```bash
kubectl get hpa -n dev -w
# NAME          TARGETS              REPLICAS
# backend-hpa   cpu: <unknown>/60%   3     ← Metrics Server not installed yet
```

### After Metrics Server + load generator deployed

Wait ~30 seconds for metrics to accumulate. Then watch:

```bash
kubectl get hpa -n dev -w
# NAME          TARGETS        REPLICAS
# backend-hpa   cpu: 84%/60%   3     ← Above target, HPA triggers scale-up
# backend-hpa   cpu: 86%/60%   5     ↑ 5 replicas now
# backend-hpa   cpu: 55%/60%   5     ← Load spread across 5 Pods, CPU dropped
# backend-hpa   cpu: 48%/60%   5
# backend-hpa   cpu: 50%/60%   5
```

In our test, the backend scaled from **3 → 5 → 7** replicas within minutes:

```
HPA Events:
  Normal  SuccessfulRescale   New size: 5   cpu utilization above target
  Normal  SuccessfulRescale   New size: 7   cpu utilization above target
```

Meanwhile the frontend was reachable and showed backend data throughout — zero downtime.

### Check real-time CPU

```bash
kubectl top pods -n dev
# NAME                       CPU(cores)   MEMORY(bytes)
# backend-xxxxx-xxxxx        85m          34Mi
# backend-xxxxx-xxxxx        89m          34Mi
# backend-xxxxx-xxxxx        86m          34Mi
# frontend-xxxxx-xxxxx       1m           36Mi
# frontend-xxxxx-xxxxx       1m           37Mi
# load-generator-xxxxx       1124m        24Mi      ← Using 1+ full CPU core!
```

### Stop the load — watch scale down

```bash
kubectl delete deployment load-generator -n dev
kubectl get hpa -n dev -w
# backend-hpa   cpu: 10%/60%   5     ← CPU drops fast
# backend-hpa   cpu: 5%/60%    5     ← waiting for cooldown
# backend-hpa   cpu: 5%/60%    3     ← scaled back to minReplicas
```

> **Scale-down has a cooldown** (`--horizontal-pod-autoscaler-downscale-stabilization`, default 5 min). K8s waits to avoid thrashing.

---

## Complete File Tree

```
08.HPA,metrics-server,loadgenerator/
├── note.md
├── note.ipynb
├── backend/
│   ├── main.py               # FastAPI returning JSON with name + message
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── backend.yaml           # Deployment ×3 (CPU request 100m) + ClusterIP Service
│   └── hpa.yaml               # autoscaling/v2, target 60% CPU, min=3 max=10
├── frontend/
│   ├── main.py               # FastAPI calling http://backend, returning HTML
│   ├── Dockerfile
│   ├── requirements.txt
│   └── frontend.yaml          # Deployment ×2 + ClusterIP Service
└── load_generator/
    ├── main.py                # 20 threads hitting backend in a loop
    ├── Dockerfile
    ├── requirements.txt       # requests
    └── load-generator.yaml    # Deployment ×1 (image: load-generator:1.1)
```

---

## Mistakes & Fixes Log

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `kubectl` pointed at Docker Desktop, not kind | No resources found in `dev` | `kubectl config use-context kind-k8` |
| Metrics Server not installed | HPA shows `cpu: <unknown>/60%` | `kubectl apply -f components.yaml` |
| Metrics Server can't connect (kind self-signed certs) | Still `<unknown>` after install | Patch with `--kubelet-insecure-tls` flag |
| `load-generator:1.1` image not built locally | `ErrImagePull` / `ImagePullBackOff` | `docker build` + `kind load docker-image` |
| `load_generator/requirements.txt` was empty | Pod crashes on `import requests` | Add `requests` to requirements.txt |
| Wrong cluster name in `kind load docker-image` | Image not found in kind | Use `--name k8` (matching `kind get clusters`) |

---

## Key Commands

| Command | Purpose |
|---------|---------|
| `kubectl top pods -n dev` | Real-time CPU/memory per Pod |
| `kubectl top nodes` | Real-time CPU/memory per Node |
| `kubectl get hpa -n dev` | HPA status — target, current, replicas |
| `kubectl get hpa -n dev -w` | Watch HPA changes live |
| `kubectl describe hpa backend-hpa -n dev` | HPA events, scaling decisions |
| `kubectl apply -f hpa.yaml` | Create/update HPA |
| `kubectl delete hpa backend-hpa -n dev` | Remove HPA (replicas stay as-is) |
| `kubectl rollout status deployment/backend -n dev` | Track deployment changes |
| `kind load docker-image <img>:<tag> --name k8` | Load local image into kind |

---

## Key Concepts

| Concept | Key Insight |
|---------|-------------|
| **HPA** | Automatically adjusts `spec.replicas` based on CPU/memory — does NOT create Pods directly |
| **Metrics Server** | Required for HPA; aggregates per-Pod resource metrics from kubelets |
| **Resource Requests** | HPA only works if Pods have `resources.requests.cpu` set |
| **Formula** | `desiredReplicas = ceil[current × (current / target)]` |
| **Scale-up** | Fast — triggers as soon as CPU exceeds target |
| **Scale-down** | Delayed — 5 min cooldown by default to prevent thrashing |
| **Load Generator** | Simulates real traffic to demonstrate autoscaling |
| **kind + Metrics Server** | Needs `--kubelet-insecure-tls` due to self-signed kubelet certs |
| **autoscaling/v2** | Supports CPU, memory, and custom/external metrics |

## Next Up — Phase 9: Canary Deployments & Rollout Strategies

- Blue-green deployments
- Canary releases (10% → 50% → 100% traffic shift)
- Rollback strategies
- Argo Rollouts or native Deployment strategies
