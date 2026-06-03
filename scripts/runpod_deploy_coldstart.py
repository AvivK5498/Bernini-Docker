#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any


REST_BASE = "https://rest.runpod.io/v1"
BOOTSTRAP_URL = "https://raw.githubusercontent.com/AvivK5498/Bernini-Runtime/main/bootstrap_runpod.sh"


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Bernini-R on Runpod using a public CUDA image and cold-start bootstrap.")
    parser.add_argument("--name", default="Bernini-R - Coldstart")
    parser.add_argument("--template-name", default="bernini-r-coldstart")
    parser.add_argument("--image", default="nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04")
    parser.add_argument("--gpu", action="append", default=["NVIDIA H200"])
    parser.add_argument("--gpu-count", type=int, default=1)
    parser.add_argument("--workers-min", type=int, default=0)
    parser.add_argument("--workers-max", type=int, default=4)
    parser.add_argument("--idle-timeout", type=int, default=300)
    parser.add_argument("--execution-timeout-ms", type=int, default=7_200_000)
    parser.add_argument("--container-disk-gb", type=int, default=300)
    parser.add_argument("--output", default="runpod-coldstart-endpoint.json")
    args = parser.parse_args()

    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        raise SystemExit("RUNPOD_API_KEY is required")

    start_cmd = [
        "bash",
        "-lc",
        f"curl -fsSL {BOOTSTRAP_URL} -o /tmp/bootstrap_runpod.sh && bash /tmp/bootstrap_runpod.sh",
    ]
    template = create_template(api_key, args=args, start_cmd=start_cmd)
    endpoint = upsert_endpoint(api_key, args=args, template_id=template["id"])
    result = {"template": template, "endpoint": endpoint}
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


def create_template(api_key: str, *, args: argparse.Namespace, start_cmd: list[str]) -> dict[str, Any]:
    body = {
        "category": "NVIDIA",
        "containerDiskInGb": args.container_disk_gb,
        "dockerEntrypoint": [],
        "dockerStartCmd": start_cmd,
        "env": {
            "BERNINI_RUNTIME_REPO": "https://github.com/AvivK5498/Bernini-Runtime.git",
            "BERNINI_RUNTIME_BRANCH": "main",
            "BERNINI_NUM_GPUS": str(args.gpu_count),
            "BERNINI_MODEL_DIR": "/models/Bernini-R-Diffusers",
            "BERNINI_WORK_ROOT": "/tmp/bernini-jobs",
        },
        "imageName": args.image,
        "isPublic": False,
        "isServerless": True,
        "name": args.template_name,
        "ports": [],
        "readme": "Cold-start Bernini-R serverless template managed from AvivK5498/Bernini-Docker.",
        "volumeInGb": 0,
        "volumeMountPath": "/workspace",
    }
    return _rest(api_key, "POST", "/templates", body)


def upsert_endpoint(api_key: str, *, args: argparse.Namespace, template_id: str) -> dict[str, Any]:
    existing = next((item for item in _rest(api_key, "GET", "/endpoints") if item.get("name") == args.name), None)
    body = {
        "name": args.name,
        "templateId": template_id,
        "gpuTypeIds": args.gpu,
        "gpuCount": args.gpu_count,
        "workersMin": args.workers_min,
        "workersMax": args.workers_max,
        "idleTimeout": args.idle_timeout,
        "executionTimeoutMs": args.execution_timeout_ms,
        "scalerType": "QUEUE_DELAY",
        "scalerValue": 4,
        "flashboot": False,
        "minCudaVersion": "12.8",
    }
    if existing:
        return _rest(api_key, "PATCH", f"/endpoints/{existing['id']}", body)
    return _rest(api_key, "POST", "/endpoints", body)


def _rest(api_key: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{REST_BASE}{path}",
        data=data,
        method=method,
        headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            text = response.read().decode()
    except Exception as exc:
        if hasattr(exc, "read"):
            detail = exc.read().decode(errors="replace")[:2000]
            raise RuntimeError(f"{method} {path} failed: {exc}; {detail}") from exc
        raise
    return json.loads(text) if text else {}


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

