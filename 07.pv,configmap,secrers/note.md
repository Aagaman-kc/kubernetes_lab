# 07: PV/PVC, ConfigMap & Secrets — Full Walkthrough

**Stack:** Frontend (FastAPI) → Backend (FastAPI + psycopg2) → PostgreSQL (StatefulSet + PVC)

**Pattern:** Mock data first → real database later. API contract stays unchanged.

---

## Architecture

```
Browser
   │
   ▼
frontend-service (ClusterIP)          ──→  Frontend Pods ×3
   │                                           │ HTTP GET /users
   ▼                                           ▼
backend-service (ClusterIP)           ──→  FastAPI Pods ×3
   │                                           │ env vars from ConfigMap + Secret
   │                                           │ psycopg2 connection
   ▼                                           ▼
postgres-service (headless)           ──→  PostgreSQL StatefulSet (postgres-0)
                                                │
                                                ▼
                                             PVC (postgres-storage-postgres-0)
                                                │
                                                ▼
                                             PV (kind host storage)
```

---

## Step 1 — Create Cluster

```bash
kind create cluster --name k8-lab
kubectl create namespace dev
```

> ❌ Don't do `kind create namespace dev` — `kind` doesn't create namespaces. Use `kubectl`.

---

## Step 2 — Frontend

### `frontend/main.py`

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

@app.get('/',response_class=HTMLResponse)
def frontend():
    response = requests.get('http://backend')
    data= response.json
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

### `frontend/requirements.txt`

```
uvicorn
fastapi
requests
```

### `frontend/frontend.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-deployment
  namespace: dev
  labels:
    app: frontend
spec:
  replicas: 3
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
        image: frontend-07:1.0
        ports:
        - containerPort: 80

---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
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
# ❌ Don't build from root — no Dockerfile there
cd .\07.pv,configmap,secrers\frontend\
docker build -t frontend-07:1.0 .
kind load docker-image frontend-07:1.0 --name k8-lab
kubectl apply -f .\frontend.yaml

kubectl get pods -n dev
# 3/3 Running
```

---

## Step 3 — Backend v1.0 (Mock JSON)

> First build with hardcoded mock data. API stays the same when we swap to real Postgres later.

### `backend/main.py` (v1.0)

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    users = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"}
    ]
    return {"users": users}
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

### `backend/requirements.txt`

```
fastapi
uvicorn
```

### `backend/backend.yaml`

```yaml
# =============================================
# Backend Deployment — 3 replicas behind ClusterIP Service
# =============================================
# In v1.1, image becomes backend-07:1.1 and env vars
# from ConfigMap + Secret are injected here (see Step 6).
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
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
        image: backend-07:1.0
        ports:
        - containerPort: 80

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

### Commands

```bash
cd .\07.pv,configmap,secrers\backend\
docker build -t backend-07:1.0 .
kind load docker-image backend-07:1.0 --name k8-lab
kubectl apply -f .\backend.yaml

kubectl get pods -n dev
kubectl get svc -n dev
# 6 pods running (3 frontend + 3 backend)
```

```bash
# Test with port-forward
kubectl port-forward service/backend 8080:80 -n dev
```

Response at `http://localhost:8080`:
```json
{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"},{"id":3,"name":"Charlie"}]}
```

---

## Step 4 — ConfigMap & Secret Theory

### ConfigMap (non-sensitive — safe to commit)

```
DB_HOST=postgres       ✅
DB_PORT=5432           ✅
LOG_LEVEL=INFO         ✅
```

### Secret (sensitive — never commit real values)

```
DB_PASSWORD=mypassword   ❌
JWT_SECRET=abcdefgh      ❌
API_KEY=xxxxxxxxx        ❌
```

> **Base64 is encoding, NOT encryption.** Anyone can decode:
> ```bash
> echo "bXlwYXNzd29yZA==" | base64 -d   # → mypassword
> ```

### Production Repo Structure

```
project/
├── deployment.yaml          ✅
├── service.yaml             ✅
├── pvc.yaml                 ✅
├── configmap.yaml           ✅
├── secret.example.yaml      ✅  (placeholder template)
└── secret.yaml              ❌  (real credentials — never commit)
```

### Real Secret Flow in Companies

```
GitHub Actions → Secrets Manager (AWS/Vault/Azure/GCP) → K8s Secret (deploy-time only)
```

| Object | Content | Commit to Git? |
|--------|---------|----------------|
| ConfigMap | Non-sensitive settings | Usually yes |
| Secret | Passwords, keys, tokens | Never real values |
| `secret.example.yaml` | Placeholder template | Yes |
| Actual Secret | Real credentials | No — deploy-time only |

> **For this project:** `password123` is fine — local kind cluster. Final project will use secrets manager.

---

## Step 5 — PostgreSQL with Persistent Storage

### 5a. `postgres/secrets.yaml`

```yaml
# =============================================
# Secret — stores sensitive data (base64-encoded by K8s)
# =============================================
# Opaque = arbitrary key-value pairs (most common type)
# stringData accepts plain text; K8s auto-encodes to base64 on store
# NOTE: Base64 is NOT encryption — never commit real secrets to Git
apiVersion: v1
kind: Secret

metadata:
  name: postgresql-secret    # referenced by StatefulSet via secretKeyRef
  namespace: dev

type: Opaque

stringData:
  POSTGRES_USER: admin          # injected as env var into Postgres container
  POSTGRES_PASSWORD: password123
```

### 5b. `postgres/pvc.yaml`

```yaml
# =============================================
# PersistentVolumeClaim — request storage
# =============================================
# A PVC is a request for storage by a Pod.
# K8s automatically provisions a PV (or binds to an existing one) that matches.
# The Pod references this PVC — it never sees the PV directly.
# This decouples storage provisioning from Pod definitions.
apiVersion: v1
kind: PersistentVolumeClaim

metadata:
  name: postgres-pvc           # referenced by StatefulSet volume claim
  namespace: dev

spec:
  # ReadWriteOnce = single node can mount as read-write
  # Other options: ReadOnlyMany, ReadWriteMany
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi             # minimum storage capacity requested
```

### 5c. `postgres/statefulset.yaml`

> **❌ Critical gotcha:** In StatefulSet, use `volumeClaimTemplates` at `spec` level, NOT `volumes:` inside the container spec (that's a Deployment thing).

```yaml
# =============================================
# StatefulSet — PostgreSQL with persistent storage
# =============================================
# StatefulSet vs Deployment:
#   - Stable Pod identity: Pods are named postgres-0, postgres-1, etc.
#   - Ordered creation/termination (0 first, then 1, ...)
#   - Uses volumeClaimTemplates — each Pod gets its own PVC automatically
# This is ideal for stateful apps like databases.
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: dev
spec:
  # Must match the headless service name (service.yaml)
  # so each Pod gets a stable DNS: postgres-0.postgres.dev.svc.cluster.local
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16
        ports:
        - containerPort: 5432  # Postgres default port
        env:
        # --- Plain value (from ConfigMap in production) ---
        - name: POSTGRES_DB
          value: appdb          # database name to create on startup

        # --- Sensitive values from Secret (never hardcoded) ---
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgresql-secret   # must match Secret metadata.name
              key: POSTGRES_USER        # key inside the Secret
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: POSTGRES_PASSWORD

        # --- Mount the PVC to Postgres data directory ---
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data  # where Postgres stores DB files

  # =============================================
  # volumeClaimTemplates — automatic PVC per replica
  # =============================================
  # Unlike Deployment (which reuses one PVC for all replicas),
  # StatefulSet creates a dedicated PVC for each replica.
  # For 1 replica, it creates one PVC named: postgres-storage-postgres-0.
  # The volumeMount name (postgres-storage) links to this template.
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 2Gi
```

### 5d. `postgres/service.yaml`

```yaml
# =============================================
# Headless Service — stable DNS for StatefulSet Pods
# =============================================
# clusterIP: None means this is a "headless" service.
# It doesn't load-balance — instead it returns the Pod IPs directly.
# Combined with StatefulSet, each Pod gets a predictable DNS:
#   postgres-0.postgres.dev.svc.cluster.local
apiVersion: v1
kind: Service

metadata:
  name: postgres
  namespace: dev

spec:
  selector:
    app: postgres

  ports:
  - port: 5432
    targetPort: 5432

  clusterIP: None              # headless — enables direct Pod DNS
```

### Commands

```bash
kubectl apply -f .\secrets.yaml
kubectl apply -f pvc.yaml
kubectl apply -f statefulset.yaml   # ❌ first time errored → fixed → ✅
kubectl apply -f service.yaml

kubectl get pods -n dev
# postgres-0 should be Running
```

---

## Step 6 — Backend v1.1 (Real PostgreSQL)

| Aspect | v1.0 (Mock) | v1.1 (Real DB) |
|--------|-------------|----------------|
| Data source | Hardcoded JSON | PostgreSQL `users` table |
| Dependencies | fastapi, uvicorn | + psycopg2-binary |
| DB config | None | `os.getenv()` from ConfigMap + Secret |

### Updated `backend/requirements.txt`

```
fastapi
uvicorn
psycopg2-binary
```

### Updated `backend/main.py` (v1.1)

```python
from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),        # ConfigMap
    database=os.getenv("DB_NAME"),    # ConfigMap
    user=os.getenv("DB_USER"),        # Secret
    password=os.getenv("DB_PASSWORD"),# Secret
    port=os.getenv("DB_PORT", "5432") # ConfigMap
)

@app.get("/")
def get_users():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    cursor.close()
    return {"users": rows}
```

> **Key principle:** Backend reads env vars — never knows if they came from ConfigMap, Secret, or somewhere else.

### Commands — Rolling Update

```bash
cd .\backend\
docker build -t backend-07:1.1 .
kind load docker-image backend-07:1.1 --name k8-lab
kubectl apply -f backend.yaml
kubectl rollout status deployment/backend-deployment -n dev
```

Rolling update process:
```
Old Pod (v1.0)  →  New Pod (v1.1) starts  →  Old Pod drains & stops
                                 ↓
                         Repeat for all 3 replicas
```

```bash
# Verify
kubectl port-forward service/backend 8080:80 -n dev
```

Response at `http://localhost:8080` (same API contract):
```json
{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"},{"id":3,"name":"Charlie"}]}
```

---

## Complete File Tree

```
07.pv,configmap,secrers/
├── note.md
├── note.ipynb
├── frontend/
│   ├── main.py              # FastAPI → calls http://backend, returns HTML
│   ├── Dockerfile
│   ├── requirements.txt
│   └── frontend.yaml        # Deployment ×3 + ClusterIP Service
├── backend/
│   ├── main.py              # v1.1 with psycopg2, reads env vars
│   ├── Dockerfile
│   ├── requirements.txt
│   └── backend.yaml         # Deployment ×3 + ClusterIP Service
└── postgres/
    ├── secrets.yaml          # POSTGRES_USER, POSTGRES_PASSWORD
    ├── pvc.yaml              # 1Gi ReadWriteOnce
    ├── statefulset.yaml      # Postgres 16, volumeClaimTemplates
    └── service.yaml          # headless, clusterIP: None
```

---

## Key Concepts Summary

| Concept | Why It Matters |
|---------|---------------|
| **ConfigMap** | Non-sensitive config injected as env vars — usually safe to commit |
| **Secret** | Base64 is encoding, NOT encryption. Never commit real values |
| **secret.example.yaml** | Safe template with placeholder values — commit this instead of real secrets |
| **StatefulSet** | Stable Pod identity (`postgres-0`), ordered creation, uses `volumeClaimTemplates` (not `volumes:` in container) |
| **PVC** | Decouples storage from Pod lifecycle — data survives restarts |
| **Headless Service** | `clusterIP: None` enables direct DNS to StatefulSet Pods |
| **Rolling Update** | Zero-downtime — change image tag, K8s replaces Pods gradually |
| **Mock First** | Start with fake JSON, swap to real DB — API contract stays the same |

---

## Final Project Note

Production deployment will be manual (not committed in Git). Real `secret.yaml` will be generated at deploy time from a secrets manager.
