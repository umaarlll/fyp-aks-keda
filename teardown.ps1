# FYP Teardown Script
# Run this when done for the day to stop burning credits

Write-Host "==> Destroying all Azure resources..." -ForegroundColor Yellow
Set-Location C:\Users\umaar\projects\fyp\infra
terraform destroy -auto-approve

Write-Host "==> Done. No more charges." -ForegroundColor Green