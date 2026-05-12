# Running on Nirvana Labs

Nirvana Labs provides bare-metal-backed virtual machines optimized for high-throughput workloads. This application is deployed on a single Nirvana VM provisioned through the official Terraform provider (`nirvana-labs/nirvana`).

The provisioning flow is:

1. Terraform creates a VPC, a single subnet, and firewall rules allowing inbound SSH on port 22 and HTTP on port 8000.
2. Terraform launches one VM running Ubuntu 24.04 LTS with an Advanced Block Storage boot volume. The default instance type is `n1-standard-8`, which provides eight vCPUs and thirty-two gigabytes of memory. The extra cores matter because the LLM runs locally on the same VM and inference is CPU-bound.
3. The script `scripts/generate-inventory.sh` reads the VM's public IP from Terraform output and writes an Ansible inventory file.
4. The Ansible playbook installs Docker on the VM, copies the application source, and brings up the Docker Compose stack with `app`, `qdrant`, `postgres`, `redis`, and `ollama` services. A one-shot init container pulls the Ollama model on first start.

The deployment uses only the default Advanced Block Storage tier. No special performance tuning, replication topology, or multi-region setup is configured. The intent is to demonstrate a normal, idiomatic deployment that a developer would produce when shipping a LangChain agent to production on Nirvana for the first time.
