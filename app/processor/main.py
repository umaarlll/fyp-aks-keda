import os
import json
import time
import logging
from azure.servicebus import ServiceBusClient
from response_engine import block_ip, isolate_pod, cordon_node

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Task 13a smoke test — remove after verification
logger.info("response_engine imported successfully")

QUEUE_NAME = "log-queue"

def classify_severity(alert: dict) -> str:
    priority = alert.get("priority", "").lower()
    if priority in ["critical", "emergency"]:
        return "critical"
    elif priority in ["error", "warning"]:
        return "medium"
    else:
        return "low"

def handle_alert(alert: dict):
    severity = classify_severity(alert)
    rule = alert.get("rule", "unknown")
    output_fields = alert.get("output_fields", {})

    logger.info(f"Alert received | rule={rule} | severity={severity}")

    if severity == "critical":
        node_name = output_fields.get("k8s.node.name", "")
        if node_name:
            logger.warning(f"[TIER 3] Critical alert — cordoning node: {node_name}")
            cordon_node(node_name)
        else:
            logger.warning(f"[TIER 3] Critical alert — no node name found in output_fields")

    elif severity == "medium":
        pod_name = output_fields.get("k8s.pod.name", "")
        if pod_name:
            logger.warning(f"[TIER 2] Medium alert — isolating pod: {pod_name}")
            isolate_pod(pod_name)
        else:
            logger.warning(f"[TIER 2] Medium alert — no pod name found in output_fields")

    else:
        ip = output_fields.get("fd.sip", "")
        if ip:
            logger.info(f"[TIER 1] Low alert — blocking IP: {ip}")
            block_ip(ip)
        else:
            logger.info(f"[TIER 1] Low alert — no source IP found in output_fields")

def main():
    connection_string = os.environ["SERVICEBUS_CONNECTION_STRING"]
    logger.info("Log processor starting...")
    client = ServiceBusClient.from_connection_string(connection_string)

    with client:
        receiver = client.get_queue_receiver(queue_name=QUEUE_NAME, max_wait_time=5)
        with receiver:
            while True:
                messages = receiver.receive_messages(max_message_count=10, max_wait_time=5)
                if not messages:
                    logger.info("Queue empty, waiting...")
                    time.sleep(0.8)
                    continue

                for msg in messages:
                    try:
                        body = json.loads(str(msg))
                        handle_alert(body)
                        receiver.complete_message(msg)
                        time.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Failed to process message: {e}")
                        receiver.abandon_message(msg)

if __name__ == "__main__":
    main()

