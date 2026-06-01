variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "southeastasia"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-fyp-aks"
}

variable "project_name" {
  description = "Short name used to prefix all resources"
  type        = string
  default     = "fyp"
}