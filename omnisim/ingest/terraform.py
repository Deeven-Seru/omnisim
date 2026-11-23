"""Terraform Infrastructure as Code (IaC) Ingestion for OmniSim.

Parses Terraform HCL declarations or JSON execution plans (aws_autoscaling_group,
aws_db_instance, aws_lb, aws_elasticache) into an OmniSim UniversalState graph,
calculating hardware limits (e.g. AWS RDS max_connections formulas) to detect
production outages before 'terraform apply' runs.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from omnisim.core.state import Entity, Invariant, UniversalState

# AWS RDS PostgreSQL & MySQL default max_connections formulas:
RDS_INSTANCE_SPECS = {
    "db.t2.micro": {"ram_mb": 1024, "max_connections": 112, "base_iops": 1000},
    "db.t2.small": {"ram_mb": 2048, "max_connections": 225, "base_iops": 1500},
    "db.t2.medium": {"ram_mb": 4096, "max_connections": 412, "base_iops": 2000},
    "db.t3.micro": {"ram_mb": 1024, "max_connections": 112, "base_iops": 1000},
    "db.t3.small": {"ram_mb": 2048, "max_connections": 225, "base_iops": 1500},
    "db.t3.medium": {"ram_mb": 4096, "max_connections": 412, "base_iops": 2000},
    "db.t3.large": {"ram_mb": 8192, "max_connections": 824, "base_iops": 3000},
    "db.t4g.micro": {"ram_mb": 1024, "max_connections": 112, "base_iops": 1000},
    "db.t4g.small": {"ram_mb": 2048, "max_connections": 225, "base_iops": 1500},
    "db.t4g.medium": {"ram_mb": 4096, "max_connections": 412, "base_iops": 2000},
    "db.r6g.large": {"ram_mb": 16384, "max_connections": 1365, "base_iops": 6000},
    "db.r6g.xlarge": {"ram_mb": 32768, "max_connections": 2730, "base_iops": 12000},
}


class TerraformIngester:
    """Ingests Terraform HCL or Terraform JSON plan objects into OmniSim causal graphs."""

    @classmethod
    def parse_hcl_text(cls, hcl_text: str) -> UniversalState:
        """Lightweight robust HCL block parser for common Terraform cloud resource blocks."""
        state = UniversalState(step=0)

        # 1. Parse aws_autoscaling_group
        asg_matches = re.finditer(
            r'resource\s+"aws_autoscaling_group"\s+"([^"]+)"\s*\{([^}]+)\}',
            hcl_text,
            re.DOTALL
        )
        for m in asg_matches:
            name = m.group(1)
            body = m.group(2)
            min_size = cls._extract_int(body, "min_size", 2)
            max_size = cls._extract_int(body, "max_size", 10)
            desired = cls._extract_int(body, "desired_capacity", min_size)

            state.add_entity(Entity(
                id=f"asg_{name}",
                type="aws_autoscaling_group",
                metrics={
                    "min_size": float(min_size),
                    "max_size": float(max_size),
                    "active_instances": float(desired),
                    "concurrency_per_instance": 20.0,  # e.g., Puma / Gunicorn threads
                    "total_qps_capacity": float(desired) * 500.0,
                    "latency_ms": 15.0,
                },
                properties={"resource_name": name, "provider": "aws"}
            ))

        # 2. Parse aws_db_instance
        db_matches = re.finditer(
            r'resource\s+"aws_db_instance"\s+"([^"]+)"\s*\{([^}]+)\}',
            hcl_text,
            re.DOTALL
        )
        for m in db_matches:
            name = m.group(1)
            body = m.group(2)
            inst_class = cls._extract_str(body, "instance_class", "db.t3.medium")
            allocated_storage = cls._extract_int(body, "allocated_storage", 50)
            engine = cls._extract_str(body, "engine", "postgres")

            specs = RDS_INSTANCE_SPECS.get(inst_class, {"ram_mb": 4096, "max_connections": 412, "base_iops": 2000})
            max_conn = float(specs["max_connections"])

            state.add_entity(Entity(
                id=f"rds_{name}",
                type="aws_db_instance",
                metrics={
                    "max_connections": max_conn,
                    "active_connections": 50.0,
                    "pool_saturation": 50.0 / max_conn,
                    "storage_gb": float(allocated_storage),
                    "ram_mb": float(specs["ram_mb"]),
                    "latency_ms": 12.0,
                    "error_rate": 0.0,
                },
                properties={
                    "resource_name": name,
                    "instance_class": inst_class,
                    "engine": engine,
                }
            ))

            # Non-negotiable Production Invariant: DB connections cannot exceed AWS hard limit
            state.add_invariant(Invariant(
                name=f"Terraform RDS {name} Connection Exhaustion Trap",
                target_entity=f"rds_{name}",
                metric="pool_saturation",
                operator="<=",
                threshold=0.90,  # Critical safety boundary at 90%
                severity="CRITICAL",
                description=f"AWS RDS {name} ({inst_class}) hard limit of {max_conn:.0f} connections will be exceeded!"
            ))

        # 3. Parse aws_lb (Application Load Balancer)
        alb_matches = re.finditer(
            r'resource\s+"aws_lb"\s+"([^"]+)"\s*\{([^}]+)\}',
            hcl_text,
            re.DOTALL
        )
        for m in alb_matches:
            name = m.group(1)
            state.add_entity(Entity(
                id=f"alb_{name}",
                type="aws_lb",
                metrics={"load_qps": 1000.0, "latency_ms": 4.0, "error_rate": 0.0}
            ))

        # Auto-wire dependencies between ASG and RDS
        for asg_id in [k for k in state.entities if k.startswith("asg_")]:
            for rds_id in [k for k in state.entities if k.startswith("rds_")]:
                state.add_relation(asg_id, rds_id, "db_traffic", weight=1.0)

        return state

    @classmethod
    def parse_terraform_json(cls, tf_json: Dict[str, Any]) -> UniversalState:
        """Parses terraform show -json plan structure."""
        # Handles planned_values / root_module / resources
        state = UniversalState(step=0)
        resources = tf_json.get("planned_values", {}).get("root_module", {}).get("resources", [])
        
        # If flat resources dict is passed
        if not resources and "resource" in tf_json:
            pass

        # Synthesize from JSON representation
        for res in resources:
            r_type = res.get("type", "")
            r_name = res.get("name", "")
            values = res.get("values", {})

            if r_type == "aws_autoscaling_group":
                max_s = float(values.get("max_size", 10))
                min_s = float(values.get("min_size", 2))
                des = float(values.get("desired_capacity", min_s))
                state.add_entity(Entity(
                    id=f"asg_{r_name}",
                    type="aws_autoscaling_group",
                    metrics={"min_size": min_s, "max_size": max_s, "active_instances": des, "concurrency_per_instance": 20.0}
                ))
            elif r_type == "aws_db_instance":
                inst_cls = values.get("instance_class", "db.t3.medium")
                specs = RDS_INSTANCE_SPECS.get(inst_cls, {"ram_mb": 4096, "max_connections": 412})
                max_conn = float(specs["max_connections"])
                state.add_entity(Entity(
                    id=f"rds_{r_name}",
                    type="aws_db_instance",
                    metrics={"max_connections": max_conn, "active_connections": 50.0, "pool_saturation": 50.0 / max_conn}
                ))
                state.add_invariant(Invariant(
                    name=f"Terraform RDS {r_name} Pool Exhaustion",
                    target_entity=f"rds_{r_name}",
                    metric="pool_saturation",
                    operator="<=",
                    threshold=0.90,
                    severity="CRITICAL"
                ))

        for asg_id in [k for k in state.entities if k.startswith("asg_")]:
            for rds_id in [k for k in state.entities if k.startswith("rds_")]:
                state.add_relation(asg_id, rds_id, "db_traffic", weight=1.0)

        return state

    @staticmethod
    def _extract_int(text: str, key: str, default: int) -> int:
        match = re.search(rf'{key}\s*=\s*(\d+)', text)
        return int(match.group(1)) if match else default

    @staticmethod
    def _extract_str(text: str, key: str, default: str) -> str:
        match = re.search(rf'{key}\s*=\s*"([^"]+)"', text)
        return match.group(1) if match else default
