# Phase 6 -- Kubernetes Networking Deep Dive

## Problem: Pod-to-Pod Communication via DNS

In a multi-tier app, the frontend needs to talk to the backend using DNS names.
Kubernetes provides built-in service discovery via CoreDNS, but we need to understand:
- How DNS resolution works inside the cluster
- How Services map to Pod IPs (Endpoints)
- How to test and debug cross-service communication

## Architecture

```
Browser
    |
kubectl port-forward
    |
    v
+--------------------------+
|     Frontend Service      |
|       (ClusterIP)         |
+--------------------------+
    |
    v
+--------------------------+
|     Frontend Pod          |
|        FastAPI            |
|                           |
| GET /                     |
|     |                     |
|     v                     |
| requests.get()            |
| http://backend            |
+--------------------------+
    |
    DNS Lookup (CoreDNS)
    |
    v
+--------------------------+
|     Backend Service       |
|       (ClusterIP)         |
+--------------------------+
    |
    kube-proxy
    |
    v
+--------------------------+
|     Backend Pod           |
|        FastAPI            |
|     returns JSON          |
+--------------------------+
```

## Backend (Complete)

### `backend/app.py`

```python
from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def home():
    return {
        'message':'Hello from 06.phase',
        'note':'i will learn everything about networking, cloud, devops, mlops and architecture'
    }
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
COPY app.py .
RUN pip install -r requirements.txt
EXPOSE 80
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","80"]
```

### `backend/requirements.txt`

```
fastapi
uvicorn
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
        image: fastapi-backend:1.0
        imagePullPolicy: Never
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

## Challenge Completed

```bash
kind create cluster --name k8-lab
kubectl create namespace dev

# ---- BACKEND ----
cd backend
docker build -t fastapi-backend:1.0 .
kind load docker-image fastapi-backend:1.0 --name k8-lab
kubectl apply -f backend/backend.yaml -n dev

# ---- FRONTEND ----
cd ../frontend
docker build -t fastapi-frontend:1.0 .
kind load docker-image fastapi-frontend:1.0 --name k8-lab
kubectl apply -f frontend/frontend.yaml -n dev

# Verify both deployments
kubectl get deployments -n dev          # backend 3/3, frontend 2/2
kubectl get pods -n dev
kubectl get svc -n dev

# Test DNS resolution from inside the cluster
kubectl run net-debug --image=nicolaka/netshoot -it --rm --restart=Never -n dev -- /bin/bash
  curl http://backend                    # {"message":"Hello from 06.phase","note":"..."}
  curl http://frontend                   # Full HTML with backend data embedded
  nslookup backend                       # backend.dev.svc.cluster.local -> ClusterIP
  exit

# Access in browser
kubectl port-forward service/frontend 8080:80 -n dev
# Open http://localhost:8080
```

## DNS Deep Dive

From inside the netshoot pod, CoreDNS resolved `backend` to `backend.dev.svc.cluster.local`:

- **Short name:** `backend` works because of the `search` domains in `/etc/resolv.conf`
- **FQDN:** `backend.dev.svc.cluster.local` -> the full canonical name
- **Service IP:** `10.96.242.35` (stable, never changes unless Service is recreated)
- **Pod IPs:** `10.244.0.5`, `10.244.0.6`, `10.244.0.7` (ephemeral, can change)

| Hostname | Resolves To | Notes |
|---|---|---|
| `backend` | `10.96.242.35` | Short name via search domains |
| `backend.dev` | `10.96.242.35` | Scoped to namespace |
| `backend.dev.svc` | `10.96.242.35` | Full service scope |
| `backend.dev.svc.cluster.local` | `10.96.242.35` | FQDN |
| `10.96.0.10` | CoreDNS | Cluster DNS server |

## Concepts Learned

| Concept | Key Insight |
|---|---|
| **CoreDNS** | Internal DNS server that resolves Service names to ClusterIPs |
| **Service Discovery** | Pods find each other via DNS names, not hardcoded IPs |
| **search Domains** | `/etc/resolv.conf` has `dev.svc.cluster.local svc.cluster.local cluster.local` so `backend` alone works |
| **FQDN Pattern** | `<service>.<namespace>.svc.cluster.local` |
| **Endpoints** | Service maintains a live list of backing Pod IPs; endpoints auto-update on pod churn |
| **kube-proxy** | Implements Service VIP -> Pod IP load balancing via iptables/ipvs |
| **ClusterIP** | Service type for internal-only access; no external exposure |
| **netshoot** | Useful debug image with `curl`, `nslookup`, `dig`, `ping`, etc. |
| **kind load docker-image** | Required to make local images available to kind nodes |

## Frontend (Complete)

### `frontend/main.py`

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    response = requests.get("http://backend")
    data = response.json()

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
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]
```

### `frontend/requirements.txt`

```
fastapi
uvicorn
requests
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
        image: fastapi-frontend:1.0
        imagePullPolicy: Never
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

## Key Commands

| Command | What it does |
|---|---|
| `docker build -t name:tag .` | Build Docker image |
| `kind load docker-image name:tag --name k8-lab` | Load local image into kind |
| `kubectl apply -f file.yaml` | Create/update resources |
| `kubectl get deployments -n <ns>` | List deployments |
| `kubectl get pods -n <ns>` | List pods |
| `kubectl get svc -n <ns>` | List services with ClusterIP |
| `kubectl get endpoints -n <ns>` | See live pod IPs backing a service |
| `kubectl describe svc <name> -n <ns>` | Service details (IP, selector, ports, endpoints) |
| `kubectl run net-debug --image=nicolaka/netshoot -it --rm --restart=Never -n dev -- /bin/bash` | Launch debug pod inside cluster |
| `kubectl port-forward service/<name> 8080:80` | Forward local port to a Service |

## End-to-End Verified

```
Browser (localhost:8080)
    |
kubectl port-forward service/frontend 8080:80
    |
    v
Frontend Service (ClusterIP)
    |
    v
Frontend Pod (FastAPI)
    |
    | requests.get("http://backend")
    | DNS -> CoreDNS -> 10.96.242.35
    v
Backend Service (ClusterIP)
    |
    v
Backend Pod (FastAPI) -> returns JSON
    |
    v
Rendered HTML with backend data displayed in browser
```

Phase 6 complete. Both backend and frontend are deployed, service discovery works via CoreDNS, and the browser can access the full stack via `kubectl port-forward`.

---
