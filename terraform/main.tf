terraform {
  required_providers {
    nirvana = {
      source  = "nirvana-labs/nirvana"
      version = "~> 1.0"
    }
  }
}

provider "nirvana" {}

# VPC with a single subnet
resource "nirvana_networking_vpc" "app" {
  name        = "${var.vm_name}-vpc"
  region      = var.nirvana_region
  project_id  = var.nirvana_project_id
  subnet_name = "${var.vm_name}-subnet"
}

# Firewall: SSH for management, 8000 for the FastAPI app
resource "nirvana_networking_firewall_rule" "ssh" {
  vpc_id              = nirvana_networking_vpc.app.id
  name                = "${var.vm_name}-ssh"
  protocol            = "tcp"
  source_address      = "0.0.0.0/0"
  destination_address = nirvana_networking_vpc.app.subnet.cidr
  destination_ports   = ["22"]
}

resource "nirvana_networking_firewall_rule" "app_http" {
  vpc_id              = nirvana_networking_vpc.app.id
  name                = "${var.vm_name}-http"
  protocol            = "tcp"
  source_address      = "0.0.0.0/0"
  destination_address = nirvana_networking_vpc.app.subnet.cidr
  destination_ports   = ["8000"]
}

resource "nirvana_compute_vm" "app" {
  name              = var.vm_name
  region            = var.nirvana_region
  project_id        = var.nirvana_project_id
  instance_type     = var.nirvana_instance_type
  os_image_name     = "ubuntu-noble-2025-10-01"
  boot_volume       = { size = var.nirvana_storage_size, type = var.nirvana_storage_type }
  public_ip_enabled = true
  subnet_id         = nirvana_networking_vpc.app.subnet.id
  ssh_key           = { public_key = var.ssh_public_key }

  depends_on = [
    nirvana_networking_firewall_rule.ssh,
    nirvana_networking_firewall_rule.app_http,
  ]
}

output "vm_ip" {
  value       = nirvana_compute_vm.app.public_ip
  description = "Public IP of the deployed VM"
}

output "next_steps" {
  value = <<-EOT

    VM is ready! Next steps:

    1. Generate inventory:    ./scripts/generate-inventory.sh
    2. Deploy app:            cd ansible && ansible-playbook playbook.yml
       (first run pulls a ~2GB Ollama model and takes a few extra minutes)
    3. Test it:               curl http://${nirvana_compute_vm.app.public_ip}:8000/chat \
                                  -H "Content-Type: application/json" \
                                  -d '{"session_id":"s1","message":"What is this app?"}'

  EOT
}
