# 07: PV/PVC, ConfigMap & Secrets — Full Walkthrough

All code, files, terminal commands, and everything we did from start to end.

---

## Architecture

`
Browser
   |
   ▼
frontend-service (ClusterIP)
   |
   ▼
Frontend Pods (3)
   |  HTTP GET /users
   ▼
backend-service (ClusterIP)
   |
   ▼
FastAPI Pods (3)
   |  Reads ConfigMap & Secret
   |  psycopg connection
   ▼
postgres-service (ClusterIP)
   |
   ▼
PostgreSQL StatefulSet
   |
   ▼
PVC
   |
   ▼
PV
`

---

## Step 1 — Create Cluster

`ash
kind create cluster --name k8-lab
`

Output:
`
Creating cluster "k8-lab" ...
 ✓ Ensuring node image (kindest/node:v1.36.1)
 ✓ Preparing nodes
 ✓ Writing configuration
 ✓ Starting control-plane
 ✓ Installing CNI
 ✓ Installing StorageClass
Set kubectl context to "kind-k8-lab"
`

---

## Step 2 — Build & Deploy Frontend

### frontend/main.py
`python
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
`

### frontend/Dockerfile
`dockerfile
FROM python:3.11-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
EXPOSE 80
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]
`

### frontend/requirements.txt
`
uvicorn
fastapi
requests
`

### frontend/frontend.yaml
`yaml
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
`

### Terminal Commands

`ash
# ERROR: ran docker build from root — no Dockerfile
docker build -t frontend-07:1.0 .
`
`
ERROR: failed to build: failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
`

`ash
# ERROR: image was never built
kind load docker-image frontend-07:1.0
`
`
ERROR: image: "frontend-07:1.0" not present locally
`

`ash
# CORRECT: cd into the right directory
cd .\07.pv,configmap,secrers\frontend\

docker build -t frontend-07:1.0 .
`
`
[+] Building 2.4s (11/11) FINISHED
 => [internal] load build definition from Dockerfile
 => [internal] load metadata for docker.io/library/python:3.11-alpine
 => [internal] load build context
 => CACHED [2/5] WORKDIR /app
 => CACHED [3/5] COPY requirements.txt .
 => CACHED [4/5] RUN pip install -r requirements.txt
 => CACHED [5/5] COPY main.py .
 => exporting to image
 => => naming to docker.io/library/frontend-07:1.0
`

`ash
kind load docker-image frontend-07:1.0 --name k8-lab
`
`
Image: "frontend-07:1.0" with ID "sha256:..." not yet present on node "k8-lab-control-plane", loading...
`

`ash
# ERROR: kind does not create namespaces
kind create namespace dev
`
`
ERROR: Subcommand is required
`

`ash
# CORRECT: use kubectl to create namespace
kubectl create namespace dev
`
`
namespace/dev created
`

`ash
kubectl apply -f .\frontend.yaml
`
`
deployment.apps/frontend-deployment created
service/frontend-service created
`

`ash
# TYPO: got nods instead of nodes
kubectl get nods -n dev
`
`
error: the server doesn't have a resource type "nods"
`

`ash
kubectl get pods -n dev
`
`
NAME                                   READY   STATUS    RESTARTS   AGE
frontend-deployment-78f79b94cb-fqfqw   1/1     Running   0          26s
frontend-deployment-78f79b94cb-ghj2n   1/1     Running   0          26s
frontend-deployment-78f79b94cb-s8djk   1/1     Running   0          26s
`

---

## Step 3 — Backend v1.0 (Fake JSON)

First we build the backend with hardcoded fake data (mock-first pattern).

### backend/main.py (v1.0)
`python
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
`

### backend/Dockerfile
`dockerfile
FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY main.py .

EXPOSE 80

CMD ["uvicorn","main:app","--host","0.0.0.0","--port","80"]
`

### backend/requirements.txt
`
fastapi
uvicorn
`

### backend/backend.yaml
`yaml
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
`

### Terminal Commands

`ash
cd .\07.pv,configmap,secrers\backend\

docker build -t backend-07:1.0 .
`
`
[+] Building 10.2s (11/11) FINISHED
 => [internal] load build definition from Dockerfile
 => [internal] load metadata for python:3.11-alpine
 => [3/5] COPY requirements.txt .
 => [4/5] RUN pip install -r requirements.txt
 => [5/5] COPY main.py .
 => exporting to image
 => => naming to docker.io/library/backend-07:1.0
`

`ash
kind load docker-image backend-07:1.0 --name k8-lab
`
`
Image: "backend-07:1.0" with ID "sha256:..." not yet present on node "k8-lab-control-plane", loading...
`

`ash
kubectl apply -f .\backend.yaml
`
`
deployment.apps/backend-deployment created
service/backend created
`

`ash
kubectl get pods -n dev
`
`
NAME                                   READY   STATUS    RESTARTS   AGE
backend-deployment-5d8cffb95d-mg4d5    1/1     Running   0          16s
backend-deployment-5d8cffb95d-s28bz    1/1     Running   0          16s
backend-deployment-5d8cffb95d-z9xv2    1/1     Running   0          16s
frontend-deployment-78f79b94cb-fqfqw   1/1     Running   0          18m
frontend-deployment-78f79b94cb-ghj2n   1/1     Running   0          18m
frontend-deployment-78f79b94cb-s8djk   1/1     Running   0          18m
`

`ash
kubectl get svc -n dev
`
`
NAME               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
backend            ClusterIP   10.96.197.0     <none>        80/TCP    23s
frontend-service   ClusterIP   10.96.176.106   <none>        80/TCP    18m
`

`ash
kubectl port-forward service/backend 8080:80 -n dev
`
`
Forwarding from 127.0.0.1:8080 -> 80
Forwarding from [::1]:8080 -> 80
Handling connection for 8080...
`

Response at http://localhost:8080:
`json
{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"},{"id":3,"name":"Charlie"}]}
`

---

## Step 4 — ConfigMap & Secret Theory

### ConfigMap
`
DATABASE_HOST: postgres   ✅ Safe to publish
DATABASE_PORT: 5432       ✅ Safe to publish
LOG_LEVEL: INFO           ✅ Safe to publish
`

### Secret
`
DATABASE_PASSWORD: mypassword   ❌ Never publish
JWT_SECRET: abcdefghijklmnop    ❌ Never publish
API_KEY: xxxxxxxxx              ❌ Never publish
`

Even though Kubernetes Base64-encodes it:
`ash
echo "bXlwYXNzd29yZA==" | base64 -d
# → mypassword
`
**Base64 is encoding, NOT encryption.**

### Production Repo Structure
`
project/
├── deployment.yaml          ✅
├── service.yaml             ✅
├── pvc.yaml                 ✅
├── configmap.yaml           ✅
├── secret.example.yaml      ✅ (template with placeholders)
└── secret.yaml              ❌ Never (real credentials)
`

### Real Secret Flow in Companies
`
GitHub Actions
    ↓
AWS Secrets Manager / Vault / Azure Key Vault / Google Secret Manager
    ↓
Kubernetes Secret (created during deployment)
`

### Rule of Thumb
| Object | Content | Commit to Git? |
|--------|---------|----------------|
| ConfigMap | Non-sensitive settings | Usually yes |
| Secret | Passwords, keys, tokens | Never real values |
| secret.example.yaml | Placeholder template | Yes |
| Actual Secret | Real credentials | No — deploy-time only |

### For This Learning Project
We use DATABASE_PASSWORD: password123 because it runs only on a local kind cluster. Acceptable for learning. Final project will be done manually (not committed).

---

## Step 5 — PostgreSQL with Persistent Storage

### 5a. Secret (postgres/secrets.yaml)
`yaml
apiVersion: v1
kind: Secret

metadata:
  name: postgresql-secret
  namespace: dev

type: Opaque

# we are using stringData
# later k8 convert it into base64
stringData:
  POSTGRES_USER: admin
  POSTGRES_PASSWORD: password123
`

### 5b. PVC (postgres/pvc.yaml)
`yaml
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
`

### 5c. StatefulSet (postgres/statefulset.yaml)

**Version 1 — BROKEN (has volumes: inside container spec):**
`yaml
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
        # BAD: volumes: inside container spec — Deployment style
        volumes:
        - name: postgres-storage
          persistentVolumeClaim:
            claimName: postgres-pvc
  volumeClaimTemplates: []
`

**Version 2 — FIXED (uses volumeClaimTemplates at spec level):**
`yaml
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
          storage: 10Gi
`

### 5d. Service (postgres/service.yaml)
`yaml
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

  clusterIP: None
`

### Terminal Commands

`ash
# Move to postgres directory
cd ..
cd .\postgres\

kubectl apply -f .\secrets.yaml
`
`
secret/postgresql-secret created
`

`ash
kubectl apply -f pvc.yaml
`
`
persistentvolumeclaim/postgres-pvc created
`

`ash
kubectl get pvc -n dev
`
`
NAME           STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
postgres-pvc   Pending                                      standard       26s
`

`ash
kubectl get secret -n dev
`
`
NAME                TYPE     DATA   AGE
postgresql-secret   Opaque   2      3m49s
`

`ash
# ERROR: first StatefulSet version had volumes: inside container spec
kubectl apply -f statefulset.yaml
`
`
Error from server (BadRequest): error when creating "statefulset.yaml":
StatefulSet in version "v1" cannot be handled as a StatefulSet:
strict decoding error: unknown field "spec.template.spec.containers[0].volumes"
`

`ash
# FIXED: removed volumes: from container, used volumeClaimTemplates instead
kubectl apply -f statefulset.yaml
`
`
statefulset.apps/postgres created
`

`ash
kubectl apply -f service.yaml
`
`
service/postgres created
`

`ash
kubectl get pods -n dev
`
`
NAME                                   READY   STATUS              RESTARTS   AGE
backend-deployment-5d8cffb95d-mg4d5    1/1     Running             0          41m
backend-deployment-5d8cffb95d-s28bz    1/1     Running             0          41m
backend-deployment-5d8cffb95d-z9xv2    1/1     Running             0          41m
frontend-deployment-78f79b94cb-fqfqw   1/1     Running             0          59m
frontend-deployment-78f79b94cb-ghj2n   1/1     Running             0          59m
frontend-deployment-78f79b94cb-s8djk   1/1     Running             0          59m
postgres-0                             0/1     ContainerCreating   0          22s
`

---

## Step 6 — Backend v1.1 (Real Postgres)

### Updated backend/requirements.txt
`
fastapi
uvicorn
psycopg2-binary
`

### Updated backend/main.py (v1.1)
`python
from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT", "5432")
)

@app.get("/")
def get_users():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    cursor.close()
    return {"users": rows}
`

**Important:** We're NOT writing host="postgres" or password="password123". Instead we read from environment variables.

Config source:
`
ConfigMap           Secret
   |                   |
DB_HOST              DB_USER
DB_NAME              DB_PASSWORD
DB_PORT
   |                   |
   +-- os.getenv() ---+
          |
    Backend (never knows origin)
`

### Terminal Commands

`ash
cd .\backend\

docker build -t backend-07:1.1 .
`
`
[+] Building 13.2s (11/11) FINISHED
 => [internal] load build definition from Dockerfile
 => [internal] load metadata for python:3.11-alpine
 => [4/5] RUN pip install -r requirements.txt
 => [5/5] COPY main.py .
 => exporting to image
 => => naming to docker.io/library/backend-07:1.1
`

`ash
kind load docker-image backend-07:1.1 --name k8-lab
`
`
Image: "backend-07:1.1" with ID "sha256:..." not yet present on node "k8-lab-control-plane", loading...
`

`ash
kubectl apply -f backend.yaml
`
`
deployment.apps/backend-deployment unchanged
service/backend unchanged
`

`ash
kubectl rollout status deployment/backend-deployment -n dev
`
`
deployment "backend-deployment" successfully rolled out
`

### Rolling Update Process
`
Old Pod (v1.0)
    |
    v
New Pod (v1.1) created
    |
    v
Old Pod terminated
    |
    v
Repeat for all 3 replicas
`

### Verify
`ash
kubectl port-forward service/backend 8080:80 -n dev
`
`
Forwarding from 127.0.0.1:8080 -> 80
Forwarding from [::1]:8080 -> 80
Handling connection for 8080...
`

Response at http://localhost:8080:
`json
{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"},{"id":3,"name":"Charlie"}]}
`

---

## Complete File Tree

`
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
`

---

## Key Concepts Summary

| Concept | Why It Matters |
|---------|---------------|
| **ConfigMap** | Non-sensitive config injected as env vars — usually safe to commit |
| **Secret** | Base64 is encoding, NOT encryption. Never commit real values |
| **secret.example.yaml** | Safe template with placeholder values — commit this instead |
| **StatefulSet** | Stable Pod identity (postgres-0), ordered creation, uses volumeClaimTemplates |
| **PVC** | Decouples storage from Pod — data survives restarts |
| **Headless Service** | clusterIP: None — direct DNS to StatefulSet Pods |
| **Rolling Update** | Zero-downtime — change image tag, K8s replaces Pods gradually |
| **Mock First** | Start with fake JSON, swap to real DB — API contract stays same |

## For Final Project
We will do the production deployment manually (not committed in Git). The secret.yaml with real credentials will be generated at deploy time from a secrets manager.
