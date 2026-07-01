# 07: PV/PVC, ConfigMap & Secrets — Full Walkthrough

> **Stack:** Frontend (FastAPI) → Backend (FastAPI + psycopg2) → PostgreSQL (StatefulSet + PVC)
>
> **Pattern:** Mock data first → real database later. API contract stays unchanged.

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
```

```
Creating cluster "k8-lab" ...
 ✓ Ensuring node image (kindest/node:v1.36.1)
 ✓ Preparing nodes
 ✓ Writing configuration
 ✓ Starting control-plane
 ✓ Installing CNI
 ✓ Installing StorageClass
Set kubectl context to "kind-k8-lab"
```

---

## Step 2 — Build & Deploy Frontend

### Files

<details>
<summary><code>frontend/main.py</code></summary>

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
</details>

<details>
<summary><code>frontend/Dockerfile</code></summary>

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]
```
</details>

<details>
<summary><code>frontend/requirements.txt</code></summary>

```
uvicorn
fastapi
requests
```
</details>

<details>
<summary><code>frontend/frontend.yaml</code></summary>

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
</details>

### Commands

```bash
# ❌ Wrong directory — no Dockerfile here
docker build -t frontend-07:1.0 .
# ERROR: failed to read dockerfile: open Dockerfile: no such file or directory

# ❌ Image was never built
kind load docker-image frontend-07:1.0
# ERROR: image: "frontend-07:1.0" not present locally

# ✅ cd into the right directory
cd .\07.pv,configmap,secrers\frontend\
docker build -t frontend-07:1.0 .
kind load docker-image frontend-07:1.0 --name k8-lab
```

```bash
# ❌ kind doesn't create namespaces
kind create namespace dev
# ERROR: Subcommand is required

# ✅ use kubectl
kubectl create namespace dev
kubectl apply -f .\frontend.yaml
```

```bash
# Verify
kubectl get pods -n dev
```

```
NAME                                   READY   STATUS    RESTARTS   AGE
frontend-deployment-78f79b94cb-fqfqw   1/1     Running   0          26s
frontend-deployment-78f79b94cb-ghj2n   1/1     Running   0          26s
frontend-deployment-78f79b94cb-s8djk   1/1     Running   0          26s
```

> **💡 Mistakes made:** `docker build` from root, `kind create namespace`, `kubectl get nods` (typo)

---

## Step 3 — Backend v1.0 (Mock JSON)

> First build with hardcoded data. API stays same when we swap to real DB later.

### Files

<details>
<summary><code>backend/main.py</code> (v1.0 — mock)</summary>

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
</details>

<details>
<summary><code>backend/Dockerfile</code></summary>

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]
```
</details>

<details>
<summary><code>backend/requirements.txt</code></summary>

```
fastapi
uvicorn
```
</details>

<details>
<summary><code>backend/backend.yaml</code></summary>

```yaml
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
</details>

### Commands

```bash
cd .\07.pv,configmap,secrers\backend\
docker build -t backend-07:1.0 .
kind load docker-image backend-07:1.0 --name k8-lab
kubectl apply -f .\backend.yaml
```

```bash
kubectl get pods -n dev
kubectl get svc -n dev
```

```
NAME                                   READY   STATUS    RESTARTS   AGE
backend-deployment-5d8cffb95d-mg4d5    1/1     Running   0          16s
backend-deployment-5d8cffb95d-s28bz    1/1     Running   0          16s
backend-deployment-5d8cffb95d-z9xv2    1/1     Running   0          16s
frontend-deployment-78f79b94cb-fqfqw   1/1     Running   0          18m
frontend-deployment-78f79b94cb-ghj2n   1/1     Running   0          18m
frontend-deployment-78f79b94cb-s8djk   1/1     Running   0          18m

NAME               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
backend            ClusterIP   10.96.197.0     <none>        80/TCP    23s
frontend-service   ClusterIP   10.96.176.106   <none>        80/TCP    18m
```

```bash
# Test
kubectl port-forward service/backend 8080:80 -n dev
```

```
Forwarding from 127.0.0.1:8080 -> 80
Forwarding from [::1]:8080 -> 80
Handling connection for 8080...
```

**Response** at `http://localhost:8080`:
```json
{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"},{"id":3,"name":"Charlie"}]}
```

---

## Step 4 — ConfigMap & Secret Theory

### ConfigMap (non-sensitive — safe to commit)

```
DATABASE_HOST: postgres   ✅
DATABASE_PORT: 5432       ✅
LOG_LEVEL: INFO           ✅
```

### Secret (sensitive — never commit real values)

```
DATABASE_PASSWORD: mypassword   ❌
JWT_SECRET: abcdefghijklmnop    ❌
API_KEY: xxxxxxxxx              ❌
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
├── secret.example.yaml      ✅  (template with placeholders)
└── secret.yaml              ❌  (real credentials — never)
```

### Real Secret Flow in Companies

```
GitHub Actions → Secrets Manager (AWS/Vault/Azure/GCP) → K8s Secret (deploy-time only)
```

### Rule of Thumb

| Object | Content | Commit to Git? |
|--------|---------|----------------|
| ConfigMap | Non-sensitive settings | Usually yes |
| Secret | Passwords, keys, tokens | Never real values |
| `secret.example.yaml` | Placeholder template | Yes |
| Actual Secret | Real credentials | No — deploy-time only |

### For This Learning Project

We use `password123` because it runs only on a local kind cluster. Acceptable for learning. The final project will use secret management (not committed).

---

## Step 5 — PostgreSQL with Persistent Storage

### 5a. Secret — stores DB credentials

<details>
<summary><code>postgres/secrets.yaml</code></summary>

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-secret
  namespace: dev
type: Opaque

# stringData accepts plain text; K8s auto-encodes to base64 on store
stringData:
  POSTGRES_USER: admin
  POSTGRES_PASSWORD: password123
```
</details>

### 5b. PVC — requests persistent storage

<details>
<summary><code>postgres/pvc.yaml</code></summary>

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: dev
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```
</details>

### 5c. StatefulSet — the critical part

> **Key difference from Deployment:** StatefulSet uses `volumeClaimTemplates` at `spec` level, NOT `volumes:` inside the container spec.

<details>
<summary><code>postgres/statefulset.yaml</code> (final working version)</summary>

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: dev
spec:
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
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: appdb
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data

  # volumeClaimTemplates — NOT volumes: inside container
  # Each replica gets its own PVC automatically: postgres-storage-postgres-0
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 2Gi
```
</details>

> **❌ Known error:** First version had `volumes:` inside the container spec (Deployment style). Got:
> ```
> Error: unknown field "spec.template.spec.containers[0].volumes"
> ```
> **Fix:** Remove `volumes:` from container, use `volumeClaimTemplates` at `spec` level.

### 5d. Headless Service — enables stable DNS

<details>
<summary><code>postgres/service.yaml</code></summary>

```yaml
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
  clusterIP: None    # headless → enables postgres-0.postgres.dev.svc.cluster.local
```
</details>

### Commands

```bash
kubectl apply -f .\secrets.yaml
kubectl apply -f pvc.yaml
kubectl apply -f statefulset.yaml   # ❌ first time: error → fixed → ✅
kubectl apply -f service.yaml
```

```bash
kubectl get secret -n dev
kubectl get pvc -n dev
kubectl get pods -n dev
```

```
NAME                TYPE     DATA   AGE
postgresql-secret   Opaque   2      3m49s

NAME           STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
postgres-pvc   Pending                                      standard       26s

NAME                                   READY   STATUS              RESTARTS   AGE
backend-deployment-5d8cffb95d-mg4d5    1/1     Running             0          41m
backend-deployment-5d8cffb95d-s28bz    1/1     Running             0          41m
backend-deployment-5d8cffb95d-z9xv2    1/1     Running             0          41m
frontend-deployment-78f79b94cb-fqfqw   1/1     Running             0          59m
frontend-deployment-78f79b94cb-ghj2n   1/1     Running             0          59m
frontend-deployment-78f79b94cb-s8djk   1/1     Running             0          59m
postgres-0                             0/1     ContainerCreating   0          22s
```

---

## Step 6 — Backend v1.1 (Real PostgreSQL)

### What Changed

| Aspect | v1.0 (Mock) | v1.1 (Real DB) |
|--------|-------------|----------------|
| Data source | Hardcoded JSON | PostgreSQL table `users` |
| Dependencies | fastapi, uvicorn | + psycopg2-binary |
| DB config | None | `os.getenv()` from ConfigMap + Secret |

### Updated Files

<details>
<summary><code>backend/requirements.txt</code></summary>

```
fastapi
uvicorn
psycopg2-binary
```
</details>

<details>
<summary><code>backend/main.py</code> (v1.1)</summary>

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
</details>

> **Key principle:** Backend reads env vars — it never knows whether they came from ConfigMap, Secret, or somewhere else. The pod spec wires them in.

```
ConfigMap                Secret
   │                       │
DB_HOST                  DB_USER
DB_NAME                  DB_PASSWORD
DB_PORT
   │                       │
   └──── os.getenv() ─────┘
            │
       Backend (agnostic)
```

### Rolling Update

```bash
cd .\backend\
docker build -t backend-07:1.1 .
kind load docker-image backend-07:1.1 --name k8-lab
kubectl apply -f backend.yaml
kubectl rollout status deployment/backend-deployment -n dev
```

```
deployment "backend-deployment" successfully rolled out
```

**Process:**
```
Old Pod (v1.0)  →  New Pod (v1.1) starts  →  Old Pod drains & stops
                                 ↓
                         Repeat for all 3 replicas
```

### Verify

```bash
kubectl port-forward service/backend 8080:80 -n dev
```

**Response** at `http://localhost:8080`:
```json
{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"},{"id":3,"name":"Charlie"}]}
```

> Same output as v1.0 — because the API contract didn't change. Only the data source changed underneath.

---

## Complete File Tree

```
07.pv,configmap,secrers/
├── note.md
├── note.ipynb
├── backend/
│   ├── main.py                    (v1.1 with psycopg2, reads env vars)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── backend.yaml               (Deployment + ClusterIP Service)
├── frontend/
│   ├── main.py                    (calls http://backend, returns HTML)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── frontend.yaml              (Deployment + ClusterIP Service)
└── postgres/
    ├── secrets.yaml               (POSTGRES_USER, POSTGRES_PASSWORD)
    ├── pvc.yaml                   (1Gi ReadWriteOnce)
    ├── statefulset.yaml           (Postgres 16, volumeClaimTemplates)
    └── service.yaml               (headless, clusterIP: None)
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

We will do the production deployment manually (not committed in Git). The actual `secret.yaml` with real credentials will be generated at deploy time from a secrets manager.
