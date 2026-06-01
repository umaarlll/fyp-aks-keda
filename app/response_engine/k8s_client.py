import logging
from kubernetes import client, config

logger = logging.getLogger(__name__)

_core_v1 = None
_networking_v1 = None

def get_core_v1() -> client.CoreV1Api:
    global _core_v1
    if _core_v1 is None:
        _load_config()
        _core_v1 = client.CoreV1Api()
    return _core_v1

def get_networking_v1() -> client.NetworkingV1Api:
    global _networking_v1
    if _networking_v1 is None:
        _load_config()
        _networking_v1 = client.NetworkingV1Api()
    return _networking_v1

def _load_config():
    try:
        config.load_incluster_config()
        logger.info("K8s client: loaded in-cluster config")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("K8s client: loaded local kubeconfig (dev mode)")