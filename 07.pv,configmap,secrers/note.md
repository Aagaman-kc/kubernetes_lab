# 07: PersistentVolume, ConfigMap & Secrets

## ConfigMap
- Stores non-sensitive app config (e.g., `DATABASE_HOST=postgres`, `LOG_LEVEL=INFO`)
- Safe to commit to Git if it contains no sensitive data
- Many open-source projects publish ConfigMaps publicly

## Secret
- Stores sensitive data: passwords, API keys, JWT tokens
- **Base64 is encoding, not encryption** — anyone can decode it instantly
- **Never commit real Secret values** to Git

## Best Practice: `secret.example.yaml`
- Commit a template with placeholder values (e.g., `your_password`)
- Developers clone the repo and fill in their own credentials

## Real Secrets in Production
Secrets are never stored in Git. They come from:
- CI/CD pipelines → AWS Secrets Manager / Vault / Azure Key Vault / GCP Secret Manager → Kubernetes Secret
- Or created imperatively: `kubectl create secret generic ...`
- `secret.yaml` is generated during deployment, not committed

## Rule of Thumb
| Object | Content | Commit to Git? |
|--------|---------|----------------|
| ConfigMap | Non-sensitive settings | Usually yes |
| Secret | Passwords, keys, tokens | Never real values |
| secret.example.yaml | Placeholder template | Yes |
| Actual Secret | Real credentials | No — created at deploy time |

## For This Learning Project
- We will use values like `DATABASE_PASSWORD: postgres123` — acceptable because it runs only on a local kind cluster for learning
- The final project will be done manually (not committed)
