# 07: PersistentVolume, ConfigMap & Secrets

## What We Did — Full Workflow

### Step 1: Cluster Setup
```bash
kind create cluster --name k8-lab
kubectl create namespace dev
```
**Errors made:** `kind create namespace dev` ✗ (wrong — `kind` doesn't create namespaces). Fixed with `kubectl create namespace dev`.

---

### Step 2: Frontend Deployment
```bash
cd 07.pv,configmap,secrers/frontend
docker build -t frontend-07:1.0 .
kind load docker-image frontend-07:1.0 --name k8-lab
kubectl apply -f frontend.yaml
```
**Errors made:** Initially ran `docker build` from root (no Dockerfile) ✗. Had to `cd` into the correct directory first.

Result: 3 frontend Pods + ClusterIP service.

---

### Step 3: Backend v1.0 — Fake JSON
```python
# backend/main.py — hardcoded mock data
@app.get("/")
def home():
    users = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"}
    ]
    return {"users": users}
```
```bash
cd 07.pv,configmap,secrers/backend
docker build -t backend-07:1.0 .
kind load docker-image backend-07:1.0 --name k8-lab
kubectl apply -f backend.yaml
kubectl port-forward service/backend 8080:80 -n dev
```
**Why fake data first?** This is a standard dev pattern — start with mock data, swap to real DB later. API contract stays the same.

---

### Step 4: ConfigMap & Secret Theory

**ConfigMap** — stores non-sensitive config (e.g., `DB_HOST=postgres`, `LOG_LEVEL=INFO`). Usually safe to commit to Git.

**Secret** — stores sensitive data (passwords, API keys, JWT tokens). **Never commit real values** to Git.

| Object | Content | Commit to Git? |
|--------|---------|----------------|
| ConfigMap | Non-sensitive settings | Usually yes |
| Secret | Passwords, keys, tokens | Never real values |
| `secret.example.yaml` | Placeholder template | Yes |
| Actual Secret | Real credentials | No — created at deploy time |

**Key insight:** Base64 is **encoding, not encryption**:
```bash
echo "bXlwYXNzd29yZA==" | base64 -d
# → mypassword
```

**Production flow for secrets:**
```
CI/CD → AWS Secrets Manager / Vault / Azure Key Vault → K8s Secret
```
Or imperatively:
```bash
kubectl create secret generic backend-secret --from-literal=DB_PASSWORD=mypassword
```

**For this learning project:** We use placeholder values like `password123` because it runs only on a local kind cluster. In production, secrets are never committed.

---

### Step 5: PostgreSQL — Persistent Storage

#### 5a. Secret (`secrets.yaml`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-secret
  namespace: dev
type: Opaque
stringData:
  POSTGRES_USER: admin
  POSTGRES_PASSWORD: password123
```
```bash
kubectl apply -f secrets.yaml
```

#### 5b. PVC (`pvc.yaml`)
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
```bash
kubectl apply -f pvc.yaml
```
**Note:** PVC was in `Pending` state initially — normal until a Pod claims it.

#### 5c. StatefulSet (`statefulset.yaml`)
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
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 2Gi
```
```bash
kubectl apply -f statefulset.yaml
```
**Critical error encountered:** ✗
```
Error: unknown field "spec.template.spec.containers[0].volumes"
```
**Fix:** In a StatefulSet, persistent storage goes in `volumeClaimTemplates` at `spec` level — **not** inside `spec.template.spec.containers[0].volumes`. The first attempt had `volumes:` under the container spec (which is valid for Deployments but **not** StatefulSets).

#### 5d. Headless Service (`service.yaml`)
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
  clusterIP: None   # ← headless — enables direct Pod DNS
```
```bash
kubectl apply -f service.yaml
```
**Why headless?** `clusterIP: None` enables DNS resolution directly to Pod IPs: `postgres-0.postgres.dev.svc.cluster.local`. StatefulSet requires this for stable network identity.

---

### Step 6: Backend v1.1 — Real Postgres Connection

Updated `main.py` to read config from environment variables (no hardcoded values):
```python
from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),        # from ConfigMap
    database=os.getenv("DB_NAME"),    # from ConfigMap
    user=os.getenv("DB_USER"),        # from Secret
    password=os.getenv("DB_PASSWORD"),# from Secret
    port=os.getenv("DB_PORT", "5432") # from ConfigMap
)

@app.get("/")
def get_users():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    cursor.close()
    return {"users": rows}
```
**Why env vars?** The backend never knows where values come from — it just calls `os.getenv()`. K8s injects them from:
- **ConfigMap** → `DB_HOST`, `DB_NAME` (non-sensitive)
- **Secret** → `DB_USER`, `DB_PASSWORD` (sensitive)

```bash
docker build -t backend-07:1.1 .
kind load docker-image backend-07:1.1 --name k8-lab
kubectl apply -f backend.yaml
kubectl rollout status deployment/backend-deployment -n dev
```

---

### Step 7: Rolling Update

Changed image tag in `backend.yaml` from `backend-07:1.0` → `backend-07:1.1`.

```
Old Pod  →  New Pod (1.1) created  →  Old Pod terminated
                    ↓
            Repeat for all replicas
```
- Zero-downtime — new Pods start before old ones shut down
- Rollout status tracked via `kubectl rollout status`

---

### Step 8: Verification
```bash
kubectl port-forward service/backend 8080:80 -n dev
# Response:
# {"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"},{"id":3,"name":"Charlie"}]}
```

---

## Architecture
```
Browser
   │
   ▼
frontend-service (ClusterIP)
   │
   ▼
Frontend Pods (3)
   │  HTTP GET /users
   ▼
backend-service (ClusterIP)
   │
   ▼
FastAPI Pods (3)
   │  Reads ConfigMap & Secret (env vars)
   │  psycopg2 connection
   ▼
postgres-service (ClusterIP — headless)
   │
   ▼
PostgreSQL StatefulSet (postgres-0)
   │
   ▼
PVC (postgres-storage-postgres-0)
   │
   ▼
PV (kind host — local storage)
```

---

## Key Concepts
| Concept | Why It Matters |
|---------|---------------|
| **ConfigMap** | Non-sensitive config injected as env vars — safe to commit |
| **Secret** | Sensitive data injected via `secretKeyRef` — base64 ≠ encryption, never commit real values |
| **StatefulSet** | Stable Pod identity (`postgres-0`), ordered creation, `volumeClaimTemplates` |
| **PVC** | Decouples storage from Pod — data survives Pod restarts |
| **Headless Service** | `clusterIP: None` — enables direct DNS to StatefulSet Pods |
| **Rolling Update** | Zero-downtime replacement by changing image tag |
| **Mock → Real** | Start with fake data, swap to real DB without changing architecture |

---

## For Final Project
We will do the full production deployment manually (not committed). The `secret.yaml` will be generated at deploy time, not stored in Git.
