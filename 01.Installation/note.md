# Phase 1 — Installation + Cluster Setup

I started this phase by installing the essential Kubernetes tools and creating my very first cluster.

> The goal: understand what a cluster is and how the tools fit together.

## Tool Overview

| Tool | What it does |
|------|-------------|
| **kubectl** | CLI that talks to the K8s API server |
| **kind** | K8s clusters inside Docker containers |
| **Docker** | Container runtime — kind needs it |
| **k9s** | Terminal UI (optional, nice-to-have) |

## 1. Install kubectl

I installed the Kubernetes CLI:

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
kubectl version --client
```

I also added this alias so I can type `k` instead of `kubectl`:

```bash
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
echo 'complete -o default -F __start_kubectl k' >> ~/.bashrc
source ~/.bashrc
```

## 2. Install kind

I installed **Kin**d = **K**ubernetes **in** **D**ocker:

```bash
curl -Lo kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
chmod +x kind
sudo mv kind /usr/local/bin/
kind version
```

## 3. Docker Desktop (Windows + WSL2)

I checked Docker is accessible inside WSL:

```bash
docker ps
```

| Problem | Fix |
|---------|-----|
| `command not found` | Docker → Settings → WSL Integration → Enable your distro |
| `Cannot connect to daemon` | Start Docker Desktop, then `wsl --shutdown` in PowerShell, reopen Ubuntu |

## 4. Install k9s (Optional)

I installed a terminal UI for K8s (like `htop` for clusters):

```bash
curl -Lo k9s.tar.gz https://github.com/derailed/k9s/releases/latest/download/k9s_Linux_amd64.tar.gz
tar -xvf k9s.tar.gz
sudo mv k9s /usr/local/bin/
```

## Project 1: "My First Cluster"

I created my first Kubernetes cluster:

```bash
kind create cluster --name my-first-cluster
```

Output:

```
Creating cluster "my-first-cluster" ...
 ✓ Ensuring node image 🖼
 ✓ Preparing nodes 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-my-first-cluster"
```

Then I verified it:

```bash
kubectl get nodes
kubectl cluster-info
kubectl config current-context
```

### Must-Know Commands

| Command | What it does |
|---------|-------------|
| `kubectl get nodes` | List all nodes in the cluster |
| `kubectl cluster-info` | See the cluster endpoints |
| `kubectl config view` | See your kubeconfig |
| `kubectl get pods -A` | List all pods in all namespaces |
| `kubectl describe node <name>` | Detailed info about a node |
| `kind get clusters` | List kind clusters |
| `kind delete cluster --name my-first-cluster` | Destroy it |

## Bonus: Multi-Node Cluster

I went further and created a multi-node cluster with a config file:

```bash
kind delete cluster --name my-first-cluster

cat <<EOF | kind create cluster --name k8-lab --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
EOF

kubectl get nodes
```

```
NAME                 STATUS   ROLES           AGE   VERSION
k8-lab-control-plane Ready    control-plane   1m    v1.31.0
k8-lab-worker        Ready    <none>          1m    v1.31.0
```

Now I had a **real** control-plane + worker setup — like production.

## Common Issues I Hit

| Problem | Likely Cause | Fix |
|---------|-------------|------|
| `kind` not found | Not in PATH | `sudo mv kind /usr/local/bin/` |
| `kind create cluster` hangs | Docker not running | Start Docker Desktop |
| `kubectl get nodes` → empty | Wrong context | `kubectl config use-context kind-...` |
| Docker permission denied | Not in docker group | `sudo usermod -aG docker $USER && newgrp docker` |
| Port conflict | Another cluster running | `kind delete clusters --all` |

## What I Learned

- **kubectl** = HTTP client for the API server
- **kind** = K8s inside Docker containers
- **Cluster** = control-plane + worker(s)
- **Control-plane** = API server, scheduler, controller manager, etcd
- **Worker node** runs your app pods
- **System pods** live in `kube-system` namespace
- `kubectl get nodes` — cluster members and health
- `kubectl cluster-info` — API server address
- `kind delete cluster` — instant cleanup

---

**Next → Phase 2: Your First Pod**
