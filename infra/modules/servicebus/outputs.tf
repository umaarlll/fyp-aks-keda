output "namespace_name" {
  value = azurerm_servicebus_namespace.main.name
}

output "queue_name" {
  value = azurerm_servicebus_queue.logs.name
}

output "primary_connection_string" {
  value     = azurerm_servicebus_namespace.main.default_primary_connection_string
  sensitive = true
}