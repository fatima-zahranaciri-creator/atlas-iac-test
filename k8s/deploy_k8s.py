import os
from pyinfra.operations import apt, server, files
from pyinfra import host

# Créer le fichier placeholder sur Machine 01 pour files.put
open("/tmp/k8s_join_command.txt", "a").close()

# Étape 0 : Nettoyer ancien repo kubernetes si présent
server.shell(
    name="Supprimer ancien repo Kubernetes si present",
    commands=["rm -f /etc/apt/sources.list.d/kubernetes.list"],
    _sudo=True,
)

# Étape 1 : Mise à jour système
apt.update(
    name="Mise a jour apt",
    _sudo=True,
)

# Étape 2 : Installation Docker + outils
apt.packages(
    name="Installation Docker et outils",
    packages=["docker.io", "apt-transport-https", "ca-certificates", "curl", "gnupg", "lsb-release", "containerd", "sshpass"],
    _sudo=True,
    update=True,
)

# Étape 3 : Configurer containerd
server.shell(
    name="Configurer containerd",
    commands=[
        "mkdir -p /etc/containerd",
        "containerd config default | tee /etc/containerd/config.toml",
        "sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml",
        "systemctl restart containerd",
        "systemctl enable containerd",
    ],
    _sudo=True,
)

# Étape 4 : Désactiver le swap
server.shell(
    name="Desactiver swap",
    commands=[
        "swapoff -a",
        "sed -i '/swap/d' /etc/fstab",
    ],
    _sudo=True,
)

# Étape 5 : Activer modules kernel requis
server.shell(
    name="Activer modules kernel",
    commands=[
        "modprobe overlay",
        "modprobe br_netfilter",
        "echo 'overlay' | tee /etc/modules-load.d/k8s.conf",
        "echo 'br_netfilter' | tee -a /etc/modules-load.d/k8s.conf",
        "echo 'net.bridge.bridge-nf-call-iptables=1' | tee /etc/sysctl.d/k8s.conf",
        "echo 'net.bridge.bridge-nf-call-ip6tables=1' | tee -a /etc/sysctl.d/k8s.conf",
        "echo 'net.ipv4.ip_forward=1' | tee -a /etc/sysctl.d/k8s.conf",
        "sysctl --system",
    ],
    _sudo=True,
)

# Étape 6 : Ajout repo Kubernetes v1.28
server.shell(
    name="Ajout repo Kubernetes v1.28",
    commands=[
        "mkdir -p /etc/apt/keyrings",
        "rm -f /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
        "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | gpg --batch --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
        'echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list',
    ],
    _sudo=True,
)

# Étape 7 : Installation Kubernetes
apt.packages(
    name="Installation kubeadm kubelet kubectl",
    packages=["kubeadm", "kubelet", "kubectl"],
    _sudo=True,
    update=True,
)

# Étape 8 : Activation kubelet
server.shell(
    name="Activation kubelet",
    commands=["systemctl enable kubelet", "systemctl start kubelet"],
    _sudo=True,
)

# ============================================================
# Étapes Control Plane (Server 02) + Sync Workers (Server 03)
# Les 4 étapes "sync" alignent l'exécution pour que
# "Joindre le cluster" se passe APRÈS "Generer join command"
# ============================================================

if "control_plane" in host.groups:
    server.shell(
        name="Init Control Plane",
        commands=[
            "kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=10.163.93.206 --ignore-preflight-errors=NumCPU 2>&1 | tee /tmp/kubeadm_init.log",
        ],
        _sudo=True,
    )
if "workers" in host.groups:
    server.shell(name="Sync 1: attente init control plane", commands=["echo ok"])

if "control_plane" in host.groups:
    server.shell(
        name="Setup kubeconfig pour fnaciri",
        commands=[
            "mkdir -p /home/fnaciri/.kube",
            "cp -f /etc/kubernetes/admin.conf /home/fnaciri/.kube/config",
            "chown fnaciri:fnaciri /home/fnaciri/.kube/config",
        ],
        _sudo=True,
    )
if "workers" in host.groups:
    server.shell(name="Sync 2: attente kubeconfig", commands=["echo ok"])

if "control_plane" in host.groups:
    server.shell(
        name="Installation Flannel CNI",
        commands=[
            "KUBECONFIG=/home/fnaciri/.kube/config kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml",
        ],
        _sudo=True,
    )
if "workers" in host.groups:
    server.shell(name="Sync 3: attente flannel", commands=["echo ok"])

if "control_plane" in host.groups:
    server.shell(
        name="Generer et sauvegarder join command",
        commands=[
            "kubeadm token create --print-join-command | tee /tmp/join_command.txt",
        ],
        _sudo=True,
    )
    files.get(
        name="Copier join command vers Machine 01",
        src="/tmp/join_command.txt",
        dest="/tmp/k8s_join_command.txt",
    )
if "workers" in host.groups:
    server.shell(name="Sync 4: attente join command", commands=["echo ok"])
    server.shell(name="Sync 5: attente copie join command", commands=["echo ok"])

# ============================================================
# Étape finale : Worker rejoint le cluster
# PyInfra envoie le fichier de Machine 01 vers Server 03
# ============================================================
if "workers" in host.groups:
    files.put(
        name="Envoyer join command vers Server 03",
        src="/tmp/k8s_join_command.txt",
        dest="/tmp/join_command.txt",
        _sudo=True,
    )
    server.shell(
        name="Joindre le cluster Kubernetes",
        commands=[
            "bash /tmp/join_command.txt --ignore-preflight-errors=NumCPU",
        ],
        _sudo=True,
    )

