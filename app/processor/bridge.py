import os
import json
import logging
import random
import time
import threading
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from kubernetes import client, config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

CONNECTION_STRING = os.environ["SERVICEBUS_CONNECTION_STRING"]
QUEUE_NAME = "log-queue"

RULES = [
    ("Terminal shell in container", "Warning"),
    ("Sensitive file opened", "Error"),
    ("Outbound connection to C2", "Critical"),
    ("Privilege escalation detected", "Critical"),
    ("Suspicious process spawned", "Notice"),
]

RATE_MAP = {
    "off": 0,
    "low": 1,
    "medium": 3,
    "high": 8,
}

state = {"level": "off"}
lock = threading.Lock()
last_sent_time = [0.0]

# Load kubeconfig
try:
    config.load_kube_config()
except Exception:
    config.load_incluster_config()

k8s_apps = client.AppsV1Api()

def generate_alert():
    rule, priority = random.choice(RULES)
    return {
        "rule": rule,
        "priority": priority,
        "source_ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "pod": f"app-pod-{random.randint(1,10)}",
        "namespace": "default"
    }

@app.get("/")
def index():
    return FileResponse("app/processor/static/index.html")

app.mount("/static", StaticFiles(directory="app/processor/static"), name="static")

@app.post("/send")
def send_message():
    global last_sent_time

    level = state["level"]
    rate = RATE_MAP.get(level, 0)

    if rate == 0:
        return {"status": "skipped", "reason": "level is off"}

    min_interval = 1.0 / rate

    with lock:
        now = time.time()
        if now - last_sent_time[0] < min_interval:
            return {"status": "skipped", "reason": "rate limited"}
        last_sent_time[0] = now

    try:
        alert = generate_alert()
        client_sb = ServiceBusClient.from_connection_string(CONNECTION_STRING)
        with client_sb:
            sender = client_sb.get_queue_sender(queue_name=QUEUE_NAME)
            with sender:
                sender.send_messages(ServiceBusMessage(json.dumps(alert)))
                logger.info(f"Sent: {alert['rule']} [{alert['priority']}]")
        return {"status": "ok", "rule": alert["rule"], "level": level}
    except Exception as e:
        logger.error(f"Failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/level/{level}")
def set_level(level: str):
    if level not in RATE_MAP:
        return {"status": "error", "message": f"Invalid level. Use: {list(RATE_MAP.keys())}"}
    state["level"] = level
    logger.info(f"Level set to: {level}")
    return {"status": "ok", "level": level}

@app.get("/level")
def get_level():
    return {"level": state["level"], "rate": RATE_MAP[state["level"]]}

@app.get("/stats")
def get_stats():
    try:
        deployment = k8s_apps.read_namespaced_deployment("log-processor", "default")
        pods = deployment.status.ready_replicas or 0
    except Exception as e:
        logger.error(f"Failed to get pod count: {e}")
        pods = 0

    try:
        sb_client = ServiceBusClient.from_connection_string(CONNECTION_STRING)
        with sb_client:
            receiver = sb_client.get_queue_receiver(queue_name=QUEUE_NAME, max_wait_time=1)
            props = sb_client.get_queue_runtime_properties(QUEUE_NAME)
            queue_depth = props.active_message_count
    except Exception as e:
        logger.error(f"Failed to get queue depth: {e}")
        queue_depth = 0

    return {"pods": pods, "queue_depth": queue_depth}

@app.get("/health")
def health():
    return {"status": "ok"}