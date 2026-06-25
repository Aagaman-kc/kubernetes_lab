# Phase 5 — Backend + Frontend Website Using K8s

## Problem: Frontend Needs to Talk to Backend

A static website alone isn't enough. Real applications have:
- A **frontend** (HTML/CSS/JS) served to the user's browser
- A **backend** (API server) that processes requests and returns data

Inside Kubernetes, these are separate Deployments with separate Services. The challenge: **how does the frontend reach the backend?**

```
User's Browser
      |
   Frontend (nginx)  ──→ serves HTML
      |
   Backend (FastAPI) ──→ returns JSON data
```

## Solution: Nginx Reverse Proxy + K8s Service Discovery

Two independent Deployments, each with a ClusterIP Service:
- **Frontend**: nginx serving `index.html`, proxies `/api` requests to the backend
- **Backend**: FastAPI returning JSON at the root `/` endpoint

The frontend's nginx config uses `proxy_pass` to forward `/api` requests to the `backend` Service inside the cluster. Kubernetes DNS resolves `backend` to the correct Service IP automatically.

```
Browser → Frontend Service → nginx → proxy_pass /api → Backend Service → FastAPI Pod
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Kubernetes Cluster             │
│                                                  │
│  ┌──────────────────┐   ┌──────────────────┐    │
│  │  frontend Deployment│   │  backend Deployment│    │
│  │  (2 replicas)     │   │  (3 replicas)     │    │
│  │                    │   │                    │    │
│  │  ┌──────────────┐ │   │  ┌──────────────┐ │    │
│  │  │ nginx:alpine │ │   │  │ Python 3.11  │ │    │
│  │  │ port 80      │ │   │  │ FastAPI      │ │    │
│  │  └──────────────┘ │   │  │ uvicorn:80   │ │    │
│  └────────┬─────────┘   │  └──────────────┘ │    │
│           │              └────────┬─────────┘    │
│  ┌────────▼─────────┐   ┌────────▼─────────┐    │
│  │ frontend Service  │   │ backend Service   │    │
│  │ ClusterIP:80      │   │ ClusterIP:80      │    │
│  └──────────────────┘   └──────────────────┘    │
└─────────────────────────────────────────────────┘
```

## Manifests

### `fastapi-backend/main.py`

```python
from fastapi import FastAPI
from datetime import datetime
app = FastAPI()

@app.get("/")
def root():
    return {
        "message": "hello from aagaman",
        "time": datetime.now().isoformat()
    }
```

**Key point:** The `@` decorator is required. Without it, FastAPI never registers the route and returns 404 for all requests.

### `fastapi-backend/Dockerfile`

```dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY main.py .
RUN pip install fastapi uvicorn
EXPOSE 80
CMD ["uvicorn","main:app","--host", "0.0.0.0", "--port", "80"]
```

### `fastapi-backend/backend.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
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
        - name: api
          image: fastapi-backend:1.0
          ports:
            - containerPort: 80

---

apiVersion: v1
kind: Service
metadata:
  name: backend
  labels:
    app: backend
spec:
  selector:
    app: backend
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

### `frontend/index.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>K8s Full-Stack Demo</title>
</head>
<body>
    <h1>Frontend in Kubernetes</h1>
    <div id="output">Loading data from backend...</div>
    <script>
        fetch('/api')
            .then(response => response.json())
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
```

**Key point:** The fetch calls `/api` which nginx proxies to the backend. The response fields (`message`, `time`) must match what the backend returns.

### `frontend/nginx.conf`

```nginx
worker_processes 1;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html;
        }

        location /api {
            proxy_pass http://backend:80/;
        }
    }
}
```

**Key point:** The trailing slash on `proxy_pass http://backend:80/;` strips the `/api` prefix. A request to `/api` becomes `/` on the backend.

### `frontend/Dockerfile`

```dockerfile
FROM nginx:alpine
RUN rm -rf /etc/nginx/conf.d
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

### `frontend/frontend.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
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
        - name: web
          image: frontend:1.0
          ports:
            - containerPort: 80

---

apiVersion: v1
kind: Service
metadata:
  name: frontend
  labels:
    app: frontend
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

## Concepts Learned

| Concept | Key Insight |
|---|---|
| **Multi-Service Architecture** | Frontend and backend run as separate Deployments with separate Services |
| **Nginx Reverse Proxy** | `proxy_pass` forwards requests from one Service to another inside the cluster |
| **Service Discovery** | Nginx uses `backend` as hostname — K8s DNS resolves it to the backend Service IP |
| **Docker Image Build** | Building images locally and loading them into kind with `kind load docker-image` |
| **Field Name Matching** | Frontend JS and backend JSON must use identical field names or the UI breaks |
| **Decorator Syntax** | Python `@app.get("/")` requires the `@` — without it, the route is never registered |

## Bugs Fixed During This Phase

### Bug 1: Missing `@` decorator in FastAPI

**Symptom:** Backend returns `{"detail":"Not Found"}` for all requests.

**Cause:** `app.get("/")` without `@` is just a function call that returns a decorator — it's immediately discarded. The route is never registered.

**Fix:**
```python
# Wrong
app.get("/")
def root():

# Correct
@app.get("/")
def root():
```

### Bug 2: Frontend/Backend field name mismatch

**Symptom:** Browser shows `Error: Cannot read properties of undefined (reading 'message')`.

**Cause:** Backend returns `"date"` but frontend JavaScript reads `data.time`.

**Fix:** Changed backend to return `"time"` instead of `"date"`:
```python
# Wrong
"date": datetime.now().isoformat()

# Correct
"time": datetime.now().isoformat()
```

## Challenge Completed

```bash
# Build Docker images
cd fastapi-backend
docker build -t fastapi-backend:1.0 .

cd ../frontend
docker build -t frontend:1.0 .

# Load into kind
kind load docker-image fastapi-backend:1.0 --name k8-lab
kind load docker-image frontend:1.0 --name k8-lab

# Apply manifests
kubectl apply -f fastapi-backend/backend.yaml
kubectl apply -f frontend/frontend.yaml

# Verify
kubectl get pods
kubectl get svc

# Test backend from frontend pod
kubectl exec <frontend-pod> -- curl -s http://backend/

# Test nginx proxy
kubectl exec <frontend-pod> -- curl -s http://localhost/api

# Access in browser
kubectl port-forward service/frontend 8080:80
# Open http://localhost:8080
```

## Key Commands

| Command | What it does |
|---|---|
| `docker build -t name:tag .` | Build Docker image from Dockerfile |
| `kind load docker-image name:tag --name cluster` | Load local Docker image into kind cluster |
| `kubectl apply -f manifest.yaml` | Create/update resources from YAML |
| `kubectl rollout restart deployment/name` | Restart pods to pick up new image |
| `kubectl port-forward service/name 8080:80` | Forward local port to a Service |
| `kubectl exec pod-name -- curl http://svc` | Test connectivity from inside a pod |

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `{"detail":"Not Found"}` | Missing `@` decorator on FastAPI route | Add `@` before `app.get("/")` |
| `Cannot read property of undefined` | Frontend JS field name doesn't match backend JSON key | Align field names between frontend and backend |
| `wget: server returned error: HTTP/1.1 404 Not Found` | nginx proxy_pass not stripping path prefix | Add trailing slash to `proxy_pass` URL |
| `ImagePullBackOff` | Image not available inside kind cluster | Use `kind load docker-image` to load local image |

## Next Up — Phase 6: Kubernetes Networking Deep Dive

- DNS-based service discovery experiments
- CoreDNS resolution inside the cluster
- Multi-tier microservices networking: Frontend → Backend → Database

---
