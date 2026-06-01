# Event-Driven Scalable Log Monitoring on Azure AKS

A Final Year Project implementing an automated security incident response pipeline on Kubernetes. Falco detects threats, KEDA scales processors based on queue depth, and a response engine takes action in under 150ms.

---

## How it works

```
Falco (eBPF threat detection)
  └── Fluent Bit DaemonSet (log collection)
        └── Log Forwarder sidecar (HTTP → Service Bus)
              └── Azure Service Bus (log-queue)
                    └── KEDA (scales on queue depth)
                          └── Log Processor (Python, 0–10 pods)
                                └── Response Engine (Kubernetes API)
```

When Falco detects a suspicious event, the log travels through the pipeline and triggers an automated response based on severity — all without human intervention.

### Response tiers

| Severity | Falco Priority | Action |
|---|---|---|
| Low | Notice | Block source IP via NetworkPolicy |
| Medium | Warning / Error | Isolate pod with deny-all NetworkPolicy |
| Critical | Critical / Emergency | Cordon node to prevent further scheduling |

---

## Stack

| Layer | Technology |
|---|---|
| Threat detection | Falco (eBPF, modern_ebpf driver) |
| Log collection | Fluent Bit 3.0 DaemonSet |
| Log forwarding | Python Flask sidecar |
| Message queue | Azure Service Bus |
| Autoscaler | KEDA (azure-servicebus trigger) |
| Log processor | Python 3.11 |
| Response engine | Python 3.11 + kubernetes client |
| Observability | Prometheus + Grafana + Loki |
| Infrastructure | Terraform (azurerm ~> 3.0) |
| Cluster | Azure AKS, Standard_B2als_v2, malaysiawest |

---

## Project structure

```
fyp/
├── startup.ps1                  # Provisions and configures everything
├── teardown.ps1                 # Destroys all Azure resources
├── app/
│   ├── processor/
│   │   ├── main.py              # Log processor — dequeues, classifies, responds
│   │   ├── bridge.py            # FastAPI bridge + Monitor 1 web app
│   │   ├── load_test.js         # K6 load test script
│   │   ├── send_test_messages.py
│   │   ├── metrics_test.py      # Scaling benchmark
│   │   ├── action_benchmark.py  # Response engine benchmark
│   │   ├── static/              # Monitor 1 frontend (index.html, style.css, app.js)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── response_engine/
│   │   ├── actions.py           # Tier 1/2/3 response implementations
│   │   └── k8s_client.py        # In-cluster Kubernetes client
│   └── forwarder/
│       ├── main.py              # Flask HTTP receiver → Service Bus
│       ├── requirements.txt
│       └── Dockerfile
├── infra/
│   ├── main.tf
│   ├── providers.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars         # gitignored — contains secrets
│   └── modules/
│       ├── aks/
│       ├── servicebus/
│       └── acr/
└── k8s/
    ├── fluent-bit.yaml          # ConfigMap + DaemonSet + forwarder sidecar
    ├── processor-deployment.yaml
    ├── scaledobject.yaml        # KEDA TriggerAuthentication + ScaledObject
    ├── rbac.yaml                # ServiceAccount + ClusterRole + ClusterRoleBinding
    └── keda-metrics-apiserver-servicemonitor.yaml
```

---

## Azure resources

All in resource group `rg-fyp-aks`, region `malaysiawest`.

| Resource | Name |
|---|---|
| AKS Cluster | `aks-fyp` |
| Service Bus Namespace | `sb-fyp-logs` |
| Service Bus Queue | `log-queue` |
| Container Registry | `acrfypfyp.azurecr.io` |

---

## Setup

### Prerequisites

- Azure CLI, Terraform v1.15.3, Docker Desktop, kubectl, Helm, Python 3.11+, K6

### Starting a session

```powershell
.\startup.ps1
```

This handles everything: Terraform apply, AKS credentials, KEDA + Falco + monitoring stack install, Kubernetes manifests, and opens Grafana, the bridge server, and K6 in separate windows.

| Interface | URL | Credentials |
|---|---|---|
| Monitor 1 (web app) | http://localhost:8888 | — |
| Monitor 2 (Grafana) | http://localhost:3000 | admin / admin123 |

> On Windows with UiTM tenant: always run `az config set core.enable_broker_on_windows=false` before `az login`. The startup script handles this automatically.

### Teardown

```powershell
.\teardown.ps1
```

---

## Demo

### Load levels

Set load level via the Monitor 1 web app, or directly:

```powershell
Invoke-WebRequest -Uri http://localhost:8888/level/low    -Method POST -UseBasicParsing
Invoke-WebRequest -Uri http://localhost:8888/level/medium -Method POST -UseBasicParsing
Invoke-WebRequest -Uri http://localhost:8888/level/high   -Method POST -UseBasicParsing
Invoke-WebRequest -Uri http://localhost:8888/level/off    -Method POST -UseBasicParsing
```

Expected pod counts on a single Standard_B2als_v2 node:

| Level | Rate | Pods |
|---|---|---|
| Low | 1 msg/s | ~1 |
| Medium | 3 msg/s | ~3–4 |
| High | 8 msg/s | ~6 (node cap) |

### Watch scaling live

```powershell
kubectl get pods -n default -w
```

### Trigger a real Falco alert

```powershell
kubectl run trigger-test --image=ubuntu --restart=Never --rm -it -- bash -c "cat /etc/shadow 2>/dev/null; exit"
```

---

## Performance

### Scaling benchmark

| Messages | Scale latency | Throughput | Total time |
|---|---|---|---|
| 10 | 27.3s | 0.30 msg/s | 53.6s |
| 50 | 32.3s | 1.32 msg/s | 63.8s |
| 100 | 28.1s | 2.98 msg/s | 59.4s |

Scaling latency is consistent (~28–32s) across all load levels — this is KEDA's polling interval, not a processing bottleneck. Throughput scales 10x as more pods are added, confirming horizontal scaling works as designed.

### Response engine latency

| Action | Latency |
|---|---|
| Tier 1 — Block IP (new policy) | ~85ms |
| Tier 1 — Block IP (duplicate) | ~47ms |
| Tier 2 — Isolate pod | ~136ms |
| Tier 3 — Cordon node | ~139ms |

All response actions complete under 150ms, enabling near real-time automated incident response.

---

## Known issues

- **WAM / Azure CLI on Windows** — UiTM Conditional Access requires `az config set core.enable_broker_on_windows=false` before every `az login`. Startup script handles this.
- **Service Bus connection string** — changes after every `terraform destroy`. Run `terraform output -raw servicebus_connection_string` to get the new value and update the Kubernetes secret.
- **VM SKU** — `Standard_B2s` and `Standard_A2_v2` are unavailable in `malaysiawest`. Use `Standard_B2als_v2`.
- **azurerm v4.x** — breaks auth on UiTM tenant. Pin to `~> 3.0`.
- **Tier 3 on single-node clusters** — cordoning the only node blocks all pod scheduling. Test scripts use a fake node name to avoid this in development.
- **ACR attachment** — lost after `terraform destroy`. Startup script re-attaches with `az aks update --attach-acr`.
