import json
import time
from azure.servicebus import ServiceBusClient, ServiceBusMessage

CONNECTION_STRING = os.environ["SERVICEBUS_CONNECTION_STRING"]
QUEUE_NAME = "log-queue"

NODE = "aks-default-fake-node-for-testing"

test_alerts = [
    # Tier 1 — low severity, needs fd.sip
    {"rule": "Outbound connection", "priority": "Notice", "output": "Unexpected outbound connection", "output_fields": {"fd.sip": "10.0.1.10"}},
    {"rule": "Network scan", "priority": "Notice", "output": "Port scan detected", "output_fields": {"fd.sip": "10.0.1.11"}},
    {"rule": "Syscall anomaly", "priority": "Notice", "output": "Unusual syscall pattern", "output_fields": {"fd.sip": "10.0.1.12"}},

    # Tier 2 — medium severity, needs k8s.pod.name
    {"rule": "Terminal shell in container", "priority": "Warning", "output": "Shell spawned in container", "output_fields": {"k8s.pod.name": "log-processor-test", "k8s.node.name": NODE}},
    {"rule": "Sensitive file opened", "priority": "Error", "output": "Sensitive file opened", "output_fields": {"k8s.pod.name": "log-processor-test", "k8s.node.name": NODE}},
    {"rule": "Write below root", "priority": "Warning", "output": "File written below root", "output_fields": {"k8s.pod.name": "log-processor-test", "k8s.node.name": NODE}},

    # Tier 3 — critical severity, needs k8s.node.name
    {"rule": "Privilege escalation", "priority": "Critical", "output": "Privilege escalation detected", "output_fields": {"k8s.node.name": NODE}},
    {"rule": "Container drift", "priority": "Critical", "output": "New executable in container", "output_fields": {"k8s.node.name": NODE}},
    {"rule": "Crypto miner", "priority": "Critical", "output": "Crypto mining activity detected", "output_fields": {"k8s.node.name": NODE}},
    {"rule": "Data exfiltration", "priority": "Critical", "output": "Large outbound data transfer", "output_fields": {"k8s.node.name": NODE}},
]

client = ServiceBusClient.from_connection_string(CONNECTION_STRING)

with client:
    sender = client.get_queue_sender(queue_name=QUEUE_NAME)
    with sender:
        for alert in test_alerts:
            msg = ServiceBusMessage(json.dumps(alert))
            sender.send_messages(msg)
            print(f"Sent: {alert['rule']} [{alert['priority']}]")
            time.sleep(0.5)

print(f"\nDone — {len(test_alerts)} messages sent.")