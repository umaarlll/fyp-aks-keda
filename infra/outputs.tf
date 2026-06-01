output "servicebus_connection_string" {
  value     = module.servicebus.primary_connection_string
  sensitive = true
}

output "acr_login_server" {
  value = module.acr.login_server
}