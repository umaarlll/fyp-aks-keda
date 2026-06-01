# Event-Driven Scalable Log Monitoring on Azure AKS

A Final Year Project (FYP) implementing an automated security incident response pipeline on Kubernetes using KEDA-based autoscaling.

## Architecture

```
Falco (threat detection)
  └── Fluent Bit (log collection)
        └── Log Forwarder sidecar (HTTP → Service Bus)
              └── Azure Service Bus (message queue)
                    └── KEDA (queue-depth autoscaler)
                          └── Log Processor (Python, scales 0–10 pods)
                                └── Response Engine (Kubernetes API actions)
```

### Response Tiers
| Severity | Priority | Action |
|---|---|---|
| Low | Notice | Tier 1 — Block source IP via NetworkPolicy |
| Medium | Warning / Error | Tier 2 — Isolate pod (label + deny-all NetworkPolicy) |
| Critical | Critical / Emergency | Tier 3 — Cordon node (prevent new scheduling) |

---

## Stack

| Component | Technology |
|---|---|
| Threat detection | Falco |
| Log collection | Fluent Bit 3.0 |
| Message queue | Azure Service Bus |
| Autoscaler | KEDA |
| Log processor | Python 3.11 + azure-servicebus |
| Response engine | Python 3.11 + kubernetes |
| Infrastructure | Terraform (azurerm ~> 3.0) |
| Container registry | Azure Container Registry |
| Cluster | Azure AKS (Standard_B2als_v2) |

---

## Project Structure

```
fyp/
├── startup.ps1                  ← rebuilds everything after terraform destroy
├── teardown.ps1                 ← destroys all resources
├── app/
│   ├── processor/
│   │   ├── main.py              ← log processor entry point
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   ├── send_test_messages.py
│   │   ├── metrics_test.py      ← scaling benchmark
│   │   └── action_benchmark.py  ← response engine benchmark
│   ├── response_engine/
│   │   ├── __init__.py
│   │   ├── actions.py           ← Tier 1/2/3 response actions
│   │   └── k8s_client.py        ← in-cluster Kubernetes client
│   └── forwarder/
│       ├── main.py              ← Flask HTTP receiver → Service Bus
│       ├── requirements.txt
│       └── Dockerfile
├── infra/
│   ├── main.tf
│   ├── providers.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars         ← gitignored
│   └── modules/
│       ├── aks/
│       ├── servicebus/
│       └── acr/
└── k8s/
    ├── fluent-bit.yaml          ← ConfigMap + DaemonSet + forwarder sidecar
    ├── processor-deployment.yaml
    ├── scaledobject.yaml        ← KEDA TriggerAuthentication + ScaledObject
    └── rbac.yaml                ← ServiceAccount + ClusterRole + ClusterRoleBinding
```

---

## Azure Resources

All resources in resource group `rg-fyp-aks`, region `malaysiawest`.

| Resource | Name |
|---|---|
| AKS Cluster | `aks-fyp` |
| Service Bus Namespace | `sb-fyp-logs` |
| Service Bus Queue | `log-queue` |
| Container Registry | `acrfypfyp.azurecr.io` |

---

## Setup

### Prerequisites
- Azure CLI
- Terraform v1.15.3
- Docker Desktop
- kubectl
- Helm
- Python 3.11+ with virtualenv

### First-time setup

```powershell
# 1. Activate Python venv
.venv\Scripts\Activate.ps1

# 2. Run startup script
.\startup.ps1
```

### Every session

```powershell
.\startup.ps1
```

> **Note:** Always run `az config set core.enable_broker_on_windows=false` before `az login` on Windows (UiTM tenant requirement).

---

## Running Tests

### Send test messages manually

```powershell
cd app/processor
# Update CONNECTION_STRING first:
# cd infra && terraform output -raw servicebus_connection_string
python send_test_messages.py
```

### Watch scaling in real time

```powershell
# Terminal 1
kubectl get pods -n default -w

# Terminal 2
kubectl logs -l app=log-processor -n default --follow
```

### Trigger a real Falco alert

```powershell
kubectl run trigger-test --image=ubuntu --restart=Never --rm -it -- bash -c "cat /etc/shadow 2>/dev/null; exit"
```

### Run scaling benchmark

```powershell
cd app/processor
python metrics_test.py
```

### Run response engine benchmark

```powershell
cd app/processor
python action_benchmark.py
```

---

## Performance Results

### Scaling Benchmark

| Messages | Scale Latency | Throughput | Total Time |
|---|---|---|---|
| 10 | 27.3s | 0.30 msg/s | 53.6s |
| 50 | 32.3s | 1.32 msg/s | 63.8s |
| 100 | 28.1s | 2.98 msg/s | 59.4s |

### Response Engine Action Latency

| Action | Latency |
|---|---|
| Tier 1 — Block IP (new policy) | ~85ms |
| Tier 1 — Block IP (duplicate) | ~47ms |
| Tier 2 — Isolate pod | ~136ms |
| Tier 3 — Cordon node | ~139ms |

**Key findings:**
- Scaling latency is consistent (~28–32s) regardless of load — KEDA polling overhead, not a processing bottleneck
- Throughput scales 10x (0.30 → 2.98 msg/s) as message volume increases — horizontal scaling working as designed
- Response engine actions complete in under 150ms — near real-time incident response
- Total processing time stays flat despite 10x message increase

---

## Known Issues / Gotchas

- UiTM Conditional Access blocks `az account get-access-token` unless WAM is disabled first — always run `az config set core.enable_broker_on_windows=false` before `az login`
- Service Bus connection string changes after every `terraform destroy` — always run `terraform output -raw servicebus_connection_string` and update the Kubernetes secret and any local scripts
- `Standard_B2s` and `Standard_A2_v2` not available in `malaysiawest` for AKS — use `Standard_B2als_v2`
- azurerm v4.x breaks auth on UiTM tenant — stay on v3.x
- After `terraform destroy`, AKS-to-ACR attachment is lost — `startup.ps1` handles this with `az aks update --attach-acr`
- Tier 3 (node cordon) will block pod scheduling on a single-node cluster — test scripts use a fake node name to avoid this

---

## Teardown

```powershell
.\teardown.ps1
```

This destroys all Azure resources. Use only when done with the project.
