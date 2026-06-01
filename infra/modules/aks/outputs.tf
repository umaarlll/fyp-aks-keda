output "cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive = true
}

output "kubelet_principal_id" {
  value = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}