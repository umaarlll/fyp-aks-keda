import os
import json
import logging
import re
from flask import Flask, request
from azure.servicebus import ServiceBusClient, ServiceBusMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

CONNECTION_STRING = os.environ["SERVICEBUS_CONNECTION_STRING"]
QUEUE_NAME = "log-queue"

def extract_json(log_str: str):
    """Extract JSON from a Fluent Bit wrapped log line."""
    # Try parsing directly first
    try:
        return json.loads(log_str)
    except json.JSONDecodeError:
        pass
    # Strip Kubernetes log prefix: "2026-...Z stdout F {...}"
    match = re.search(r'\{.*\}', log_str)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None

@app.route("/", methods=["POST"])
def receive():
    try:
        data = request.get_data(as_text=True)
        for line in data.strip().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            log_str = record.get("log", "")
            if not log_str:
                continue

            alert = extract_json(log_str)
            if not alert:
                logger.warning(f"Could not parse log, skipping: {log_str[:100]}")
                continue

            client = ServiceBusClient.from_connection_string(CONNECTION_STRING)
            with client:
                sender = client.get_queue_sender(queue_name=QUEUE_NAME)
                with sender:
                    sender.send_messages(ServiceBusMessage(json.dumps(alert)))
                    logger.info(f"Forwarded: {alert.get('rule', 'unknown')}")

        return "OK", 200
    except Exception as e:
        logger.error(f"Failed to forward: {e}")
        return "Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)