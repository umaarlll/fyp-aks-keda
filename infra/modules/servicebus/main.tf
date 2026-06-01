resource "azurerm_servicebus_namespace" "main" {
  name                = "sb-${var.project_name}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"
}

resource "azurerm_servicebus_queue" "logs" {
  name         = "log-queue"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_size_in_megabytes = 1024
  max_delivery_count    = 10
  lock_duration         = "PT1M"
  default_message_ttl   = "PT1H"
}