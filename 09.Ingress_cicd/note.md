# 09: Ingress Controller & CI/CD Pipeline — Full Walkthrough

**Goal:** Expose frontend + backend through a single NGINX Ingress endpoint (path-based routing), then automate builds and deployments with a GitHub Actions CI/CD pipeline.

**Stack:** Frontend (FastAPI + httpx) → Backend (FastAPI + psycopg2) → PostgreSQL (StatefulSet + PVC) + Ingress (NGINX) + CI/CD (GitHub Actions)

---

## Architecture

```
         User (port 30080)
                │
                ▼
        ┌───────────────┐
        │ NGINX Ingress  │  path-based routing
        │ (NodePort 30080)│  /  → frontend-service:80
        └───────┬───────┘  /api → backend-service:80
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
 frontend-service   backend-service
    (ClusterIP)       (ClusterIP)
        │               │
        ▼               ▼
   Frontend Pod      Backend Pods ×2
        │               │
        │        ┌──────┘
        │        ▼
        │   postgres (headless)
        │        │
        │        ▼
        │   PostgreSQL StatefulSet
        │        │
        │        ▼
        │   PVC (1Gi)
        │
   ─ ─ ─ ─ ─ CI/CD ─ ─ ─ ─ ─ ─
   Git push → GitHub Actions → build → push → deploy
```

**Routing Rules (Ingress):**
| Path | Destination | Description |
|------|------------|-------------|
| `/` | `frontend-service:80` | Serves HTML page with JS fetching `/api` |
| `/api` | `backend-service:80` | Returns JSON from PostgreSQL |

---

## Step 1 — Create Cluster & Namespace

```powershell
kind create cluster --name k8-lab

kubectl create namespace production
kubectl config set-context --current --namespace=production
```

---

## Step 2 — PostgreSQL with ConfigMap & Secret

### `k8s/config-and-secret.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: production
data:
  POSTGRES_DB: mydb
  POSTGRES_USER: admin
  POSTGRES_HOST: postgres
  POSTGRES_PORT: "5432"
---
apiVersion: v1
kind: Secret
metadata:
  name: backend-secret
  namespace: production
type: Opaque
data:
  POSTGRES_PASSWORD: YWRtaW4xMjM=   # admin123 (base64)
```

### `k8s/postgres.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: production
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: production
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
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: backend-config
              key: POSTGRES_DB
        - name: POSTGRES_USER
          valueFrom:
            configMapKeyRef:
              name: backend-config
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: backend-secret
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 1Gi
```

### Apply

```powershell
kubectl apply -f k8s/config-and-secret.yaml
kubectl apply -f k8s/postgres.yaml

kubectl get pods -l app=postgres -n production -w
# postgres-0   1/1   Running
```

---

## Step 3 — Backend (FastAPI + psycopg2)

### `backend/main.py`

```python
from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "mydb"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", "admin123"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

@app.on_event("startup")
def startup():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        content TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    )""")
    cur.execute("SELECT COUNT(*) FROM messages")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO messages (content) VALUES ('Hello from PostgreSQL!')")
    conn.commit()
    cur.close()
    conn.close()

@app.get("/")
def root():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT content, created_at FROM messages ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"message": row[0], "time": row[1].isoformat()}
    return {"message": "no data", "time": ""}
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
```

### `k8s/backend-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: api
        image: fastapi-backend:2.0
        ports:
        - containerPort: 80
        env:
        - name: POSTGRES_HOST
          valueFrom:
            configMapKeyRef:
              name: backend-config
              key: POSTGRES_HOST
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: backend-config
              key: POSTGRES_DB
        - name: POSTGRES_USER
          valueFrom:
            configMapKeyRef:
              name: backend-config
              key: POSTGRES_USER
        - name: POSTGRES_PORT
          valueFrom:
            configMapKeyRef:
              name: backend-config
              key: POSTGRES_PORT
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: backend-secret
              key: POSTGRES_PASSWORD
---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: production
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

### Build & Load

```powershell
cd backend
docker build -t fastapi-backend:2.0 .
kind load docker-image fastapi-backend:2.0 --name k8-lab
cd ..
```

---

## Step 4 — Frontend (FastAPI + httpx + HTML)

### `frontend/main.py`

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()
BACKEND_URL = "http://backend-service:80"

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>K8s Production App</title></head>
    <body>
        <h1>Production‑grade Kubernetes App</h1>
        <div id="output">Loading...</div>
        <script>
            fetch('/api')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('output').innerHTML =
                        `<p><strong>Message:</strong> ${data.message}</p>
                         <p><strong>Time:</strong> ${data.time}</p>`;
                })
                .catch(err => {
                    document.getElementById('output').innerText = 'Error: ' + err;
                });
        </script>
    </body>
    </html>
    """

@app.get("/api")
async def proxy_api():
    async with httpx.AsyncClient() as client:
        resp = await client.get(BACKEND_URL)
        return resp.json()
```

> **Note:** The frontend serves the HTML at `/` and proxies `/api` to the backend. Both paths are routed through the Ingress — the browser never talks directly to the backend.

### `frontend/Dockerfile`

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
```

### `k8s/frontend-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: web
        image: frontend:1.0
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: production
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

### Build & Load

```powershell
cd frontend
docker build -t frontend:1.0 .
kind load docker-image frontend:1.0 --name k8-lab
cd ..
```

### Apply Both Deployments

```powershell
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

kubectl get pods -n production
# NAME                       READY   STATUS    RESTARTS   AGE
# backend-xxxxx-xxxxx        1/1     Running   0          30s
# backend-xxxxx-xxxxx        1/1     Running   0          30s
# frontend-xxxxx-xxxxx       1/1     Running   0          30s
# postgres-0                 1/1     Running   0          5m
```

---

## Step 5 — NGINX Ingress Controller

Kind requires the NGINX Ingress Controller to be installed separately (it doesn't come built-in like cloud providers).

### Install for Kind

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

### Wait for it to be ready

```powershell
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

### Verify

```powershell
kubectl get pods -n ingress-nginx
# ingress-nginx-controller-xxxxx   1/1   Running

kubectl get svc -n ingress-nginx
# ingress-nginx-controller   NodePort   10.96.x.x   <none>   80:30080/TCP,443:30443/TCP
```

> **Key:** Kind maps port `30080` on your host machine to port `80` on the Ingress controller. No `port-forward` needed.

---

## Step 6 — Ingress Resource (Path-Based Routing)

### `k8s/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-ingress
  namespace: production
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

### Apply

```powershell
kubectl apply -f k8s/ingress.yaml
```

### Verify

```powershell
kubectl get ingress -n production
# NAME           CLASS   HOSTS   ADDRESS   PORTS   AGE
# main-ingress   nginx   *                 80      10s

kubectl describe ingress main-ingress -n production
# Rules:
#   Host        Path  Backends
#   ----        ----  --------
#   *
#               /api    backend-service:80
#               /       frontend-service:80
```

---

## Step 7 — Test the Full Stack

### Open in browser

```
http://localhost:30080/
```

You should see:

- **Title:** "Production‑grade Kubernetes App"
- **Message:** "Hello from PostgreSQL!"
- **Time:** (current timestamp)

### Direct API test

```powershell
curl http://localhost:30080/api
```

Returns:
```json
{"message":"Hello from PostgreSQL!","time":"2026-07-04T22:30:00"}
```

### Why this matters

| Method | URL | What happens |
|--------|-----|--------------|
| Browser | `http://localhost:30080/` | Ingress → frontend-service → HTML page → JS fetches `/api` |
| JS fetch | `/api` (relative) | Ingress → backend-service → PostgreSQL query → JSON |
| Direct | `http://localhost:30080/api` | Same — Ingress routes based on path prefix |

**No `port-forward` is running.** Unlike earlier phases which required `kubectl port-forward`, the Ingress permanently exposes both services through a single port (30080).

---

## Step 8 — GitHub Actions CI/CD Pipeline

### How the Pipeline Works

```
Git push to main (with changes in 09.Ingress_cicd/)
    │
    ▼
GitHub Actions triggered
    │
    ├── 1. Checkout code
    ├── 2. Log in to Docker Hub (secrets.DOCKER_USERNAME + DOCKER_PASSWORD)
    ├── 3. Build & Push Backend  → docker.io/$USER/fastapi-backend:${{ github.sha }}
    ├── 4. Build & Push Frontend → docker.io/$USER/frontend:${{ github.sha }}
    ├── 5. Set kubectl context using KUBECONFIG secret
    └── 6. Deploy: kubectl set image → rolling update with new images
```

### `deploy.yml`

```yaml
name: Build, Push & Deploy

on:
  push:
    branches: [ main ]
    paths:
      - '09.Ingress_cicd/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Log in to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build & Push Backend
      run: |
        docker build -t ${{ secrets.DOCKER_USERNAME }}/fastapi-backend:${{ github.sha }} ./09.Ingress_cicd/backend
        docker push ${{ secrets.DOCKER_USERNAME }}/fastapi-backend:${{ github.sha }}

    - name: Build & Push Frontend
      run: |
        docker build -t ${{ secrets.DOCKER_USERNAME }}/frontend:${{ github.sha }} ./09.Ingress_cicd/frontend
        docker push ${{ secrets.DOCKER_USERNAME }}/frontend:${{ github.sha }}

    - name: Set kubectl context
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBECONFIG }}

    - name: Deploy to cluster
      uses: azure/k8s-deploy@v4
      with:
        namespace: production
        manifests: |
          09.Ingress_cicd/k8s/backend-deployment.yaml
          09.Ingress_cicd/k8s/frontend-deployment.yaml
        images: |
          ${{ secrets.DOCKER_USERNAME }}/fastapi-backend:${{ github.sha }}
          ${{ secrets.DOCKER_USERNAME }}/frontend:${{ github.sha }}
```

### GitHub Secrets Required

| Secret | Value |
|--------|-------|
| `DOCKER_USERNAME` | Your Docker Hub username |
| `DOCKER_PASSWORD` | Your Docker Hub password or access token |
| `KUBECONFIG` | Base64-encoded kubeconfig (from `cat ~/.kube/config \| base64`) |

### Alternative: Pure kubectl deploy step

If you prefer not to use `azure/k8s-deploy`, replace the last step with:

```yaml
    - name: Deploy with kubectl
      run: |
        kubectl set image deployment/backend api=${{ secrets.DOCKER_USERNAME }}/fastapi-backend:${{ github.sha }} -n production
        kubectl set image deployment/frontend web=${{ secrets.DOCKER_USERNAME }}/frontend:${{ github.sha }} -n production
```

---

## Complete File Tree

```
09.Ingress_cicd/
├── note.md                              ← You are here
├── k8s/
│   ├── config-and-secret.yaml           ← ConfigMap (DB name, user, host) + Secret (password)
│   ├── postgres.yaml                    ← Headless Service + StatefulSet (postgres:15-alpine, 1Gi PVC)
│   ├── backend-deployment.yaml          ← Deployment ×2 + ClusterIP Service (env from ConfigMap + Secret)
│   ├── frontend-deployment.yaml         ← Deployment ×1 + ClusterIP Service
│   └── ingress.yaml                     ← NGINX Ingress (/ → frontend, /api → backend)
├── backend/
│   ├── main.py                          ← FastAPI with psycopg2, auto-creates messages table
│   ├── requirements.txt                 ← fastapi, uvicorn, psycopg2-binary
│   └── Dockerfile                       ← python:3.11-alpine, exposes 80
├── frontend/
│   ├── main.py                          ← FastAPI with httpx, serves HTML + proxies /api
│   ├── requirements.txt                 ← fastapi, uvicorn, httpx
│   └── Dockerfile                       ← python:3.11-alpine, exposes 80
└── .github/
    └── workflows/
        └── deploy.yml                   ← GitHub Actions: build → push → deploy on push to main
```

---

## Mistakes & Fixes Log

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Ingress controller not installed | Ingress `ADDRESS` shows `<none>` forever | `kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml` |
| Wrong namespace on Ingress resource | 404 on `localhost:30080` | Ensure Ingress is in `production` namespace where services live |
| Frontend calls wrong backend URL | JS shows error / no data | Frontend uses `http://backend-service:80` (Service DNS name) |
| Images not loaded into kind | `ErrImagePull` / `ImagePullBackOff` | `kind load docker-image <tag> --name k8-lab` for each image |
| Kubeconfig context wrong | `kubectl` commands affect wrong cluster | `kubectl config use-context kind-k8-lab` |
| Docker Desktop kubectl instead of kind | Pods not found in `production` ns | Check `kubectl config current-context` |

---

## Key Commands

| Command | Purpose |
|---------|---------|
| `kubectl apply -f k8s/ingress.yaml` | Create/update Ingress rules |
| `kubectl get ingress -n production` | List Ingress resources and their status |
| `kubectl describe ingress main-ingress -n production` | Inspect routing rules, events |
| `kubectl get svc -n ingress-nginx` | Check NodePort mappings (30080 → 80) |
| `kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=90s` | Wait for Ingress controller readiness |
| `kind load docker-image <img>:<tag> --name k8-lab` | Load local image into kind nodes |
| `kubectl set image deployment/backend api=<new-image> -n production` | Trigger rolling update (CI/CD equivalent) |
| `kubectl rollout status deployment/backend -n production` | Track rolling update progress |
| `kubectl config use-context kind-k8-lab` | Switch kubectl to kind cluster |

---

## Key Concepts

| Concept | Key Insight |
|---------|-------------|
| **Ingress** | Layer 7 routing — single entry point, path-based dispatch to different Services |
| **Ingress Controller** | The actual proxy (NGINX) that implements Ingress rules — not installed by default in kind |
| **ingressClassName** | Links the Ingress resource to a specific Ingress Controller (`nginx`) |
| **PathType: Prefix** | Matches any path starting with prefix — `/api` matches `/api`, `/api/v1`, etc. |
| **NodePort (30080)** | Kind exposes Ingress controller on host port 30080 — no port-forward needed |
| **CI/CD Pipeline** | Automates build → push → deploy — every git push triggers a rolling update |
| **GitHub Secrets** | `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `KUBECONFIG` — sensitive values injected at runtime |
| **azure/k8s-deploy** | Generic K8s deploy action — works with any cluster, not just Azure |
| **Rolling Update via CI/CD** | Pipeline calls `kubectl set image` to update deployments with new image SHA tags |
| **Single Entry Point** | Ingress consolidates all HTTP traffic through one port — simplifies networking and security |

## Next Up — Phase 10: Production Readiness & Observability

- RBAC — namespace-scoped access control
- Prometheus + Grafana monitoring stack
- AWS EKS deployment strategy
- Final production checklist
