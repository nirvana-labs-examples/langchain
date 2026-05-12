variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
}

variable "nirvana_project_id" {
  description = "Nirvana project ID (from https://dashboard.nirvanalabs.io)"
  type        = string
}

variable "nirvana_region" {
  description = "Nirvana region"
  type        = string
  default     = "us-sva-2"
}

variable "nirvana_instance_type" {
  description = "Nirvana VM instance type. n1-standard-8 recommended so Ollama CPU inference stays responsive (~10s/response on a 3B model)."
  type        = string
  default     = "n1-standard-8"
}

variable "nirvana_storage_size" {
  description = "Boot volume size in GB"
  type        = number
  default     = 64
}

variable "nirvana_storage_type" {
  description = "Storage type (abs = Advanced Block Storage)"
  type        = string
  default     = "abs"
}

variable "vm_name" {
  description = "Name for the deployed VM"
  type        = string
  default     = "langchain-app"
}
