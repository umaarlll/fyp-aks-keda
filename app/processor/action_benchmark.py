import time
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.WARNING)

from response_engine.actions import block_ip, isolate_pod, cordon_node
from kubernetes import client, config

def benchmark(name, fn, *args):
    start = time.time()
    result = fn(*args)
    elapsed = (time.time() - start) * 1000
    print(f"{name:<40} {elapsed:>8.1f}ms  result={result}")
    return elapsed

def cleanup():
    config.load_kube_config()
    networking = client.NetworkingV1Api()
    core = client.CoreV1Api()
    # Delete test NetworkPolicies
    for i in range(1, 4):
        try:
            networking.delete_namespaced_network_policy(f"block-ip-10-0-99-{i}", "default")
        except:
            pass
    # Uncordon node
    try:
        core.patch_node("aks-default-21620590-vmss000000", {"spec": {"unschedulable": False}})
    except:
        pass

print(f"\n{'='*55}")
print("ACTION BENCHMARK")
print(f"{'='*55}")
print(f"{'Action':<40} {'Time':>8}    Result")
print(f"{'-'*55}")

# Tier 1 — 3 different IPs
t1a = benchmark("Tier1: block_ip (new)",       block_ip, "10.0.99.1")
t1b = benchmark("Tier1: block_ip (duplicate)", block_ip, "10.0.99.1")
t1c = benchmark("Tier1: block_ip (new)",       block_ip, "10.0.99.2")

# Tier 2 — fake pod (404 expected)
t2a = benchmark("Tier2: isolate_pod (missing pod)", isolate_pod, "fake-pod-benchmark")

# Tier 3 — real node
t3a = benchmark("Tier3: cordon_node",          cordon_node, "aks-default-21620590-vmss000000")
t3b = benchmark("Tier3: cordon_node (repeat)", cordon_node, "aks-default-21620590-vmss000000")

print(f"\n--- SUMMARY ---")
print(f"Tier 1 avg (new policy):   {(t1a + t1c) / 2:.1f}ms")
print(f"Tier 1 (duplicate):        {t1b:.1f}ms")
print(f"Tier 2 (pod missing):      {t2a:.1f}ms")
print(f"Tier 3 avg:                {(t3a + t3b) / 2:.1f}ms")

print(f"\nCleaning up...")
cleanup()
print(f"Done.")