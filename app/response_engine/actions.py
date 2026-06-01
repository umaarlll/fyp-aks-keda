import logging
from kubernetes import client
from .k8s_client import get_core_v1, get_networking_v1

logger = logging.getLogger(__name__)


def block_ip(ip: str, namespace: str = "default") -> bool:
    """Tier 1 — Block an IP via NetworkPolicy."""
    policy_name = f"block-ip-{ip.replace('.', '-')}"
    networking = get_networking_v1()

    policy = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(name=policy_name, namespace=namespace),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(),  # applies to all pods in namespace
            policy_types=["Ingress"],
            ingress=[
                client.V1NetworkPolicyIngressRule(
                    _from=[
                        client.V1NetworkPolicyPeer(
                            ip_block=client.V1IPBlock(
                                cidr=f"{ip}/32",
                            )
                        )
                    ]
                )
            ],
        ),
    )

    try:
        networking.create_namespaced_network_policy(namespace=namespace, body=policy)
        logger.info(f"[TIER 1] NetworkPolicy created: {policy_name} in {namespace}")
        return True
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logger.info(f"[TIER 1] NetworkPolicy already exists: {policy_name}")
            return True
        logger.error(f"[TIER 1] Failed to create NetworkPolicy: {e}")
        return False


def isolate_pod(pod_name: str, namespace: str = "default") -> bool:
    """Tier 2 — Isolate a pod by labeling it and applying a deny-all NetworkPolicy."""
    core = get_core_v1()
    networking = get_networking_v1()
    policy_name = f"isolate-{pod_name}"

    # Step 1 — label the pod
    try:
        core.patch_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            body={"metadata": {"labels": {"isolated": "true"}}}
        )
        logger.info(f"[TIER 2] Pod labeled isolated: {pod_name} in {namespace}")
    except client.exceptions.ApiException as e:
        logger.error(f"[TIER 2] Failed to label pod {pod_name}: {e}")
        return False

    # Step 2 — create deny-all NetworkPolicy targeting the label
    policy = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(name=policy_name, namespace=namespace),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(
                match_labels={"isolated": "true"}
            ),
            policy_types=["Ingress", "Egress"],
        ),
    )

    try:
        networking.create_namespaced_network_policy(namespace=namespace, body=policy)
        logger.info(f"[TIER 2] Deny-all NetworkPolicy created: {policy_name} in {namespace}")
        return True
    except client.exceptions.ApiException as e:
        if e.status == 409:
            logger.info(f"[TIER 2] Isolation policy already exists: {policy_name}")
            return True
        logger.error(f"[TIER 2] Failed to create isolation policy: {e}")
        return False


def cordon_node(node_name: str) -> bool:
    """Tier 3 — Cordon a node to prevent new scheduling."""
    core = get_core_v1()

    try:
        core.patch_node(
            name=node_name,
            body={"spec": {"unschedulable": True}}
        )
        logger.info(f"[TIER 3] Node cordoned: {node_name}")
        return True
    except client.exceptions.ApiException as e:
        logger.error(f"[TIER 3] Failed to cordon node {node_name}: {e}")
        return False