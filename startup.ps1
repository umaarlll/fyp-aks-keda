# FYP Startup Script
# Run this every time you come back to work on the FYP

Write-Host "==> Logging in to Azure..." -ForegroundColor Cyan
az config set core.enable_broker_on_windows=false
az login --use-device-code

Write-Host "==> Applying Terraform..." -ForegroundColor Cyan
Set-Location C:\Users\umaar\projects\fyp\infra
terraform apply -auto-approve

Write-Host "==> Getting AKS credentials..." -ForegroundColor Cyan
az aks get-credentials --resource-group rg-fyp-aks --name aks-fyp --overwrite-existing

Write-Host "==> Attaching ACR to AKS..." -ForegroundColor Cyan
az aks update --name aks-fyp --resource-group rg-fyp-aks --attach-acr acrfypfyp

Write-Host "==> Installing KEDA..." -ForegroundColor Cyan
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm upgrade --install keda kedacore/keda --namespace keda --create-namespace

Write-Host "==> Waiting for KEDA to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod --all --namespace keda --timeout=180s

Write-Host "==> Installing Falco..." -ForegroundColor Cyan
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
helm upgrade --install falco falcosecurity/falco --namespace falco --create-namespace `
  --set driver.kind=modern_ebpf `
  --set tty=true `
  --set falco.json_output=true `
  --set falco.json_include_output_property=true

Write-Host "==> Waiting for Falco to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod --all --namespace falco --timeout=180s

Write-Host "==> Installing Prometheus + Grafana..." -ForegroundColor Cyan
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm upgrade --install kube-prom prometheus-community/kube-prometheus-stack `
  --namespace monitoring `
  --create-namespace `
  --set grafana.adminPassword="admin123" `
  --set grafana.image.tag="10.4.3" `
  --set prometheus.prometheusSpec.retention="24h" `
  --set alertmanager.enabled=false

Write-Host "==> Installing Loki..." -ForegroundColor Cyan
helm upgrade --install loki grafana/loki-stack `
  --namespace monitoring `
  --set grafana.enabled=false `
  --set prometheus.enabled=false `
  --set loki.persistence.enabled=false

Write-Host "==> Applying KEDA ServiceMonitor..." -ForegroundColor Cyan
kubectl apply -f k8s/keda-metrics-apiserver-servicemonitor.yaml

Write-Host "==> Waiting for monitoring stack to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod --all --namespace monitoring --timeout=180s

Write-Host "==> Creating Service Bus secret..." -ForegroundColor Cyan
Set-Location C:\Users\umaar\projects\fyp\infra
$connStr = terraform output -raw servicebus_connection_string
kubectl delete secret servicebus-secret --namespace default --ignore-not-found
kubectl create secret generic servicebus-secret --namespace default --from-literal=connection-string="$connStr"

Write-Host "==> Applying Kubernetes manifests..." -ForegroundColor Cyan
Set-Location C:\Users\umaar\projects\fyp
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/fluent-bit.yaml
kubectl apply -f k8s/processor-deployment.yaml

Write-Host "==> Waiting for KEDA CRDs..." -ForegroundColor Cyan
Start-Sleep -Seconds 10
kubectl apply -f k8s/scaledobject.yaml

Write-Host "==> Waiting for all pods to be ready..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod --all --namespace keda --timeout=120s
kubectl wait --for=condition=ready pod --all --namespace falco --timeout=120s
kubectl wait --for=condition=ready pod --all --namespace default --timeout=120s

Write-Host "==> Setting up Python environment..." -ForegroundColor Cyan
Set-Location C:\Users\umaar\projects\fyp
.venv\Scripts\Activate.ps1
$env:SERVICEBUS_CONNECTION_STRING = $connStr

Write-Host "==> Starting Grafana port-forward in background..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "kubectl port-forward svc/kube-prom-grafana 3000:80 -n monitoring"

Write-Host "==> Starting bridge server in background..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd C:\Users\umaar\projects\fyp; .venv\Scripts\Activate.ps1; `$env:SERVICEBUS_CONNECTION_STRING='$connStr'; uvicorn app.processor.bridge:app --port 8888"

Write-Host "==> Starting K6 load test in background..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "cd C:\Users\umaar\projects\fyp\app\processor; k6 run load_test.js"

Write-Host "" 
Write-Host "==> All done! Cluster is ready." -ForegroundColor Green
Write-Host ""
Write-Host "  Grafana:  http://localhost:3000  (admin / admin123)" -ForegroundColor Yellow
Write-Host "  Bridge:   http://localhost:8888" -ForegroundColor Yellow
Write-Host "  K6:       running in background" -ForegroundColor Yellow
Write-Host ""
kubectl get pods --all-namespaces