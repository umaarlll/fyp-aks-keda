resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

module "servicebus" {
  source              = "./modules/servicebus"
  project_name        = var.project_name
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
}

module "aks" {
  source              = "./modules/aks"
  project_name        = var.project_name
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
}

module "acr" {
  source              = "./modules/acr"
  project_name        = var.project_name
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  aks_principal_id    = module.aks.kubelet_principal_id
}