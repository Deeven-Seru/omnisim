"""Kubernetes & Cloud Native Manifest Ingestion for OmniSim.

Converts standard Kubernetes YAML/JSON topologies (Deployments, Services,
Ingresses, and ConfigMaps) directly into a queryable UniversalState graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from omnisim.core.state import Entity, Invariant, UniversalState


class KubernetesManifestIngester:
    """Ingests Kubernetes declarative configurations into OmniSim causal state graphs."""

    @staticmethod
    def parse_manifests(manifests: List[Dict[str, Any]]) -> UniversalState:
        state = UniversalState(step=0)

        for resource in manifests:
            kind = resource.get("kind", "")
            metadata = resource.get("metadata", {})
            name = metadata.get("name", "unnamed-resource")
            spec = resource.get("spec", {})

            if kind == "Deployment":
                replicas = spec.get("replicas", 1)
                template_spec = spec.get("template", {}).get("spec", {})
                containers = template_spec.get("containers", [])

                cpu_limit = 1.0
                mem_limit_mb = 1024.0
                if containers:
                    c = containers[0]
                    res = c.get("resources", {}).get("limits", {})
                    cpu_raw = res.get("cpu", "1000m")
                    mem_raw = res.get("memory", "1Gi")
                    cpu_limit = float(cpu_raw.replace("m", "")) / 1000.0 if "m" in cpu_raw else float(cpu_raw)
                    mem_limit_mb = float(mem_raw.replace("Gi", "")) * 1024.0 if "Gi" in mem_raw else 512.0

                state.add_entity(Entity(
                    id=name,
                    type="k8s_deployment",
                    metrics={
                        "replicas": float(replicas),
                        "cpu_limit": cpu_limit,
                        "memory_limit_mb": mem_limit_mb,
                        "cpu_utilization": 0.35,
                        "memory_utilization": 0.40,
                        "latency_ms": 15.0,
                        "base_latency_ms": 12.0,
                        "error_rate": 0.0,
                    },
                    properties={
                        "labels": metadata.get("labels", {}),
                        "kind": "Deployment"
                    }
                ))

                # Default Invariant: CPU utilization must remain below 85%
                state.add_invariant(Invariant(
                    name=f"{name} CPU Throttling Limit",
                    target_entity=name,
                    metric="cpu_utilization",
                    operator="<=",
                    threshold=0.85,
                    severity="CRITICAL",
                    description=f"Container {name} will be throttled if CPU > 85%."
                ))

            elif kind == "Service":
                selector = spec.get("selector", {})
                app_target = selector.get("app", "")
                state.add_entity(Entity(
                    id=f"svc-{name}",
                    type="k8s_service",
                    metrics={
                        "incoming_qps": 500.0,
                        "latency_ms": 2.0,
                        "error_rate": 0.0,
                    },
                    properties={
                        "target_app": app_target,
                        "ports": spec.get("ports", []),
                    }
                ))

                # If matching target deployment exists, wire relational traffic edge
                if app_target in state.entities:
                    state.add_relation(f"svc-{name}", app_target, "traffic_flow", weight=1.0)

            elif kind == "Ingress":
                rules = spec.get("rules", [])
                state.add_entity(Entity(
                    id=f"ingress-{name}",
                    type="k8s_ingress",
                    metrics={
                        "edge_qps": 2000.0,
                        "p99_latency_ms": 8.0,
                        "ssl_handshake_ms": 1.5,
                        "error_rate": 0.0,
                    }
                ))

                for rule in rules:
                    http_paths = rule.get("http", {}).get("paths", [])
                    for p in http_paths:
                        svc_name = p.get("backend", {}).get("service", {}).get("name", "")
                        svc_id = f"svc-{svc_name}"
                        if svc_id in state.entities:
                            state.add_relation(f"ingress-{name}", svc_id, "traffic_flow", weight=1.0)

        return state
