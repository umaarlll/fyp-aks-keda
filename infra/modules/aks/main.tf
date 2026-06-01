resource "azurerm_kubernetes_cluster" "main" {
  name                = "aks-${var.project_name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "aks-${var.project_name}"

  default_node_pool {
    name       = "default"
    node_count = 1
    vm_size    = "Standard_B2als_v2"
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "kubenet"
    load_balancer_sku = "standard"
  }

  oidc_issuer_enabled = true
}