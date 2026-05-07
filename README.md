# Atlas IaC

Infrastructure as Code pour le projet Atlas/Orion.

## Structure

k8s/
├── namespaces/     # 3 namespaces: atlas-system, atlas-core, atlas-gateway
├── rbac/           # ServiceAccount, Role, RoleBinding par namespace
└── network/        # NetworkPolicy default-deny-all par namespace

## Déploiement

kubectl apply -f k8s/namespaces/namespaces.yaml
kubectl apply -f k8s/rbac/rbac.yaml
kubectl apply -f k8s/network/network-policy.yaml
