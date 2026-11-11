"""Kubernetes inspection/ops tools, restricted to one namespace."""
from kubernetes import client, config

NAMESPACE = "mlops-agent"
config.load_kube_config()
core = client.CoreV1Api()
apps = client.AppsV1Api()

def _check_ns(ns):
    if ns != NAMESPACE:
        raise PermissionError(f"Restricted to namespace '{NAMESPACE}'")

def list_pods_and_deployments(namespace: str = NAMESPACE):
    """List pods and deployments in the approved namespace."""
    _check_ns(namespace)
    return {
        "pods": [p.metadata.name for p in core.list_namespaced_pod(namespace).items],
        "deployments": [d.metadata.name for d in apps.list_namespaced_deployment(namespace).items],
    }

def get_pod_status_and_logs(pod_name: str, namespace: str = NAMESPACE, tail_lines: int = 50):
    """Get a pod's phase and recent logs."""
    _check_ns(namespace)
    pod = core.read_namespaced_pod(pod_name, namespace)
    logs = core.read_namespaced_pod_log(pod_name, namespace, tail_lines=tail_lines)
    return {"phase": pod.status.phase, "logs": logs}

def inspect_services(namespace: str = NAMESPACE):
    """List services in the namespace with type and ports."""
    _check_ns(namespace)
    return [{"name": s.metadata.name, "type": s.spec.type, "ports": [p.port for p in s.spec.ports]}
            for s in core.list_namespaced_service(namespace).items]

def get_unhealthy_pods(namespace: str = NAMESPACE):
    """List pods that aren't ready, with restart counts."""
    _check_ns(namespace)
    out = []
    for p in core.list_namespaced_pod(namespace).items:
        statuses = p.status.container_statuses or []
        if not all(s.ready for s in statuses):
            out.append({"name": p.metadata.name, "phase": p.status.phase,
                        "restarts": sum(s.restart_count for s in statuses)})
    return out

def get_deployed_version(deployment_name: str = "iris-api", namespace: str = NAMESPACE):
    """Report the currently deployed image for a deployment."""
    _check_ns(namespace)
    return apps.read_namespaced_deployment(deployment_name, namespace).spec.template.spec.containers[0].image

def restart_deployment(deployment_name: str = "iris-api", namespace: str = NAMESPACE, confirm: bool = False):
    """Restart a deployment. Requires explicit confirm=True; approved namespace only."""
    _check_ns(namespace)
    if not confirm:
        raise PermissionError("Requires confirm=True")
    import datetime
    apps.patch_namespaced_deployment(deployment_name, namespace, {"spec": {"template": {"metadata": {
        "annotations": {"kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow().isoformat()}}}}})
    return {"restarted": deployment_name}