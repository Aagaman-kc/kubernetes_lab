# 07: PersistentVolume, ConfigMap & Secrets

## Cluster Setup
- `kind create cluster --name k8-lab`
- `kubectl create namespace dev`

## Frontend
- Built `frontend-07:1.0` from `07.pv,configmap,secrers/frontend/`
- Loaded via `kind load docker-image frontend-07:1.0 --name k8-lab`
- Applied `frontend.yaml` → 3 Pods + ClusterIP service

## Backend (v1.0 — fake JSON)
- Built `backend-07:1.0` from `07.pv,configmap,secrers/backend/`
- Applied `backend.yaml` → 3 Pods + ClusterIP service
- Verified via `kubectl port-forward service/backend 8080:80 -n dev`
- Returned hardcoded `{"users": [...]}`

## PostgreSQL — Persistent Data

Three new resource types introduced here:

### Secret — `secrets.yaml`

Stores sensitive data (base64-encoded, but **not encrypted**). Never commit real values to Git in production.

```yaml
# Secret — stores sensitive data (base64-encoded internally)
# Unlike ConfigMap, values are NOT stored in plain text.
# But base64 is encoding, NOT encryption — anyone can decode.
apiVersion: v1
kind: Secret

metadata:
  name: postgresql-secret   # referenced by StatefulSet via secretKeyRef
  namespace: dev

type: Opaque                # arbitrary key-value pairs

# stringData accepts plain text; K8s base64-encodes it on store
stringData:
  POSTGRES_USER: admin
  POSTGRES_PASSWORD: password123
```

### PVC — `pvc.yaml`

A request for storage. K8s automatically binds it to a matching PersistentVolume.

```yaml
# PersistentVolumeClaim — Pod requests storage via this
# The Pod never sees the PV directly — PVC decouples them.
apiVersion: v1
kind: PersistentVolumeClaim

metadata:
  name: postgres-pvc
  namespace: dev

spec:
  accessModes:
    - ReadWriteOnce      # single node can mount as read-write
  resources:
    requests:
      storage: 1Gi       # minimum capacity requested
```

### StatefulSet — `statefulset.yaml`

Like Deployment but for stateful apps. Stable Pod identity (`postgres-0`), ordered creation, and automatic per-Pod PVC via `volumeClaimTemplates`.

```yaml
# StatefulSet — for stateful apps (databases)
# vs Deployment: stable Pod names (postgres-0), ordered startup,
# and each replica gets its own PVC automatically.
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: dev
spec:
  serviceName: postgres           # must match headless service name
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
        # Plain value — from ConfigMap in production
        - name: POSTGRES_DB
          value: appdb

        # Sensitive values from Secret — never hardcoded
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

        # Mount PVC to Postgres data directory
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data

  # volumeClaimTemplates — creates PVC per replica
  # For 1 replica → one PVC named: postgres-storage-postgres-0
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 2Gi
```

> **Gotcha**: Initially wrote `volumes:` under `spec.template.spec.containers[0]`. Error: `unknown field "volumes"`. In StatefulSet, persistent storage must be declared via `volumeClaimTemplates` at `spec` level, not inside the container spec.

### Service — `service.yaml`

A headless ClusterIP service (`clusterIP: None`) for stable DNS lookups: `postgres-0.postgres.dev.svc.cluster.local`

## Backend (v1.1 — real Postgres)
- Updated `main.py` — reads `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` from env vars (ConfigMap + Secret)
- Build `backend-07:1.1` → `kind load docker-image backend-07:1.1 --name k8-lab`
- Rolling update via `kubectl apply -f backend.yaml` → `kubectl rollout status`
- Container image tag changed in deployment, triggering rolling update (new Pods created, old ones terminated)

## Architecture
```
Frontend → backend-service → Backend Pods → postgres-service → PostgreSQL StatefulSet → PVC → PV
```

## Key Concepts
- **ConfigMap**: non-sensitive config (DB_HOST, DB_NAME) — app reads via `os.getenv()`
- **Secret**: sensitive data (DB_USER, DB_PASSWORD) — also `os.getenv()`, no hardcoded values
- **StatefulSet**: stable network identity (`postgres-0`), ordered Pod creation
- **PVC**: decouples storage from Pod lifecycle
- **Rolling Update**: zero-downtime update by changing image tag in Deployment
