# Atlas IaC

Infrastructure as Code pour le projet Atlas/Orion.

## Structure
k8s/namespaces/  → 3 namespaces
k8s/rbac/        → Contrôle d'accès
k8s/network/     → Sécurité réseau
k8s/deploy_k8s.py → Script déploiement K8s

## Déploiement
pyinfra inventory.py k8s/deploy_k8s.py

## Manifests K8s
kubectl apply -f k8s/namespaces/namespaces.yaml
kubectl apply -f k8s/rbac/rbac.yaml
kubectl apply -f k8s/network/network-policy.yaml
