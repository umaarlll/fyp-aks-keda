import json
import time
import subprocess
import threading
from datetime import datetime
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# Paste your current connection string here
CONNECTION_STRING = os.environ["SERVICEBUS_CONNECTION_STRING"]
QUEUE_NAME = "log-queue"
NODE = "aks-default-fake-node-for-testing"

from kubernetes import client, config

def get_pod_count():
    try:
        config.load_kube_config()
        v1 = client.AppsV1Api()
        deployment = v1.read_namespaced_deployment("log-processor", "default")
        return deployment.status.ready_replicas or 0
    except Exception as e:
        print(f"Error getting pod count: {e}")
        return 0

from azure.servicebus.management import ServiceBusAdministrationClient

def get_queue_depth():
    try:
        mgmt_client = ServiceBusAdministrationClient.from_connection_string(CONNECTION_STRING)
        props = mgmt_client.get_queue_runtime_properties(QUEUE_NAME)
        return props.active_message_count
    except Exception as e:
        print(f"Error getting queue depth: {e}")
        return -1

def send_messages(count: int):
    alerts = []
    for i in range(count):
        tier = i % 3
        if tier == 0:
            alert = {"rule": f"Outbound connection {i}", "priority": "Notice", "output": "test", "output_fields": {"fd.sip": f"10.0.{i}.1"}}
        elif tier == 1:
            alert = {"rule": f"Shell in container {i}", "priority": "Warning", "output": "test", "output_fields": {"k8s.pod.name": "fake-pod", "k8s.node.name": NODE}}
        else:
            alert = {"rule": f"Privilege escalation {i}", "priority": "Critical", "output": "test", "output_fields": {"k8s.node.name": NODE}}
        alerts.append(alert)

    client = ServiceBusClient.from_connection_string(CONNECTION_STRING)
    with client:
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        with sender:
            for alert in alerts:
                sender.send_messages(ServiceBusMessage(json.dumps(alert)))

def run_test(message_count: int):
    print(f"\n{'='*50}")
    print(f"TEST: {message_count} messages")
    print(f"{'='*50}")

    # Ensure starting from 0 pods
    initial_pods = get_pod_count()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Initial pods: {initial_pods}")

    # Send messages and record time
    t_send = time.time()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending {message_count} messages...")
    send_messages(message_count)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Messages sent. Waiting for scale-up...")

    # Wait for first pod to appear
    t_first_pod = None
    while True:
        pods = get_pod_count()
        if pods > 0 and t_first_pod is None:
            t_first_pod = time.time()
            scaling_latency = t_first_pod - t_send
            print(f"[{datetime.now().strftime('%H:%M:%S')}] First pod running. Scaling latency: {scaling_latency:.1f}s | Pods: {pods}")
            break
        time.sleep(2)

    # Monitor until queue drains
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitoring queue drain...")
    t_drain_start = time.time()
    while True:
        depth = get_queue_depth()
        pods = get_pod_count()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Queue depth: {depth} | Pods: {pods}")
        if depth == 0:
            t_drained = time.time()
            throughput = message_count / (t_drained - t_send)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Queue drained. Throughput: {throughput:.2f} msg/s")
            break
        time.sleep(5)

    # Wait for scale-down
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for scale-down to 0...")
    t_scaledown_start = time.time()
    while True:
        pods = get_pod_count()
        if pods == 0:
            scaledown_time = time.time() - t_scaledown_start
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scaled to 0. Scale-down time: {scaledown_time:.1f}s")
            break
        time.sleep(5)

    total_time = time.time() - t_send
    print(f"\n--- RESULTS for {message_count} messages ---")
    print(f"Scaling latency:  {scaling_latency:.1f}s")
    print(f"Throughput:       {throughput:.2f} msg/s")
    print(f"Total time:       {total_time:.1f}s")

    return {
        "messages": message_count,
        "scaling_latency": round(scaling_latency, 1),
        "throughput": round(throughput, 2),
        "total_time": round(total_time, 1)
    }

if __name__ == "__main__":
    results = []
    for count in [10, 50, 100]:
        result = run_test(count)
        results.append(result)
        print(f"\nWaiting 60s before next test...")
        time.sleep(60)

    print(f"\n{'='*50}")
    print("FINAL SUMMARY")
    print(f"{'='*50}")
    print(f"{'Messages':<12} {'Scale Latency':<16} {'Throughput':<14} {'Total Time'}")
    print(f"{'-'*56}")
    for r in results:
        print(f"{r['messages']:<12} {r['scaling_latency']:<16} {r['throughput']:<14} {r['total_time']}")