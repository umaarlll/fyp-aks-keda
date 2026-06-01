variable "project_name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "aks_principal_id" {
  type        = string
  description = "AKS kubelet identity principal ID for ACR pull"
}