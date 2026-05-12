#!/usr/bin/env bash
# Reads the VM IP from terraform output and writes ansible/inventory/hosts.yml.

set -euo pipefail

cd "$(dirname "$0")/.."

VM_IP=$(terraform -chdir=terraform output -raw vm_ip)

if [[ -z "$VM_IP" || "$VM_IP" == "null" ]]; then
  echo "Could not read vm_ip from terraform. Did terraform apply succeed?" >&2
  exit 1
fi

cat > ansible/inventory/hosts.yml <<EOF
all:
  hosts:
    langchain-app:
      ansible_host: $VM_IP
      ansible_user: ubuntu
EOF

echo "Wrote ansible/inventory/hosts.yml -> $VM_IP"
