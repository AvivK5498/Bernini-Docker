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
BOOTSTRAP_URL = "https://raw.githubusercontent.com/AvivK5498/Bernini-Runtime/main/bootstrap_gradio_pod.sh"


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy a persistent Runpod pod running Bernini Gradio.")
    parser.add_argument("--name", default="Bernini-R Gradio Pod")
    parser.add_argument("--template-name", default="bernini-r-gradio-pod")
    parser.add_argument("--image", default="pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel")
    parser.add_argument("--gpu", action="append", default=["NVIDIA H200"])
    parser.add_argument("--gpu-count", type=int, default=1)
    parser.add_argument("--container-disk-gb", type=int, default=300)
    parser.add_argument("--volume-gb", type=int, default=200)
    parser.add_argument("--network-volume-id", default="")
    parser.add_argument("--data-center-id", default="")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--interruptible", action="store_true")
    parser.add_argument("--output", default="runpod-gradio-pod.json")
    args = parser.parse_args()

    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        raise SystemExit("RUNPOD_API_KEY is required")

    start_cmd = (
        "apt-get update && "
        "apt-get install -y --no-install-recommends curl ca-certificates && "
        f"curl -fsSL {BOOTSTRAP_URL} -o /tmp/bootstrap_gradio_pod.sh && "
        "bash /tmp/bootstrap_gradio_pod.sh"
    )
    template = create_template(api_key, args=args, start_cmd=start_cmd)
    pod = create_pod(api_key, args=args, template_id=template["id"])
    result = {"template": template, "pod": pod}
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


def create_template(api_key: str, *, args: argparse.Namespace, start_cmd: str) -> dict[str, Any]:
    body = {
        "category": "NVIDIA",
        "containerDiskInGb": args.container_disk_gb,
        "dockerEntrypoint": ["bash", "-lc"],
        "dockerStartCmd": [start_cmd],
        "env": {
            "BERNINI_MODEL_DIR": "/workspace/models/Bernini-R-Diffusers",
            "BERNINI_GRADIO_PORT": str(args.port),
            "BERNINI_NUM_GPUS": str(args.gpu_count),
            "HF_HOME": "/workspace/.hf-cache",
        },
        "imageName": args.image,
        "isPublic": False,
        "isServerless": False,
        "name": args.template_name,
        "ports": [f"{args.port}/http", "8888/http", "22/tcp"],
        "readme": "Persistent Bernini-R Gradio pod template managed from AvivK5498/Bernini-Docker.",
        "volumeInGb": args.volume_gb,
        "volumeMountPath": "/workspace",
    }
    return _rest(api_key, "POST", "/templates", body)


def create_pod(api_key: str, *, args: argparse.Namespace, template_id: str) -> dict[str, Any]:
    body = {
        "name": args.name,
        "imageName": args.image,
        "templateId": template_id,
        "gpuTypeIds": args.gpu,
        "gpuCount": args.gpu_count,
        "gpuTypePriority": "availability",
        "ports": [f"{args.port}/http", "8888/http", "22/tcp"],
        "volumeInGb": args.volume_gb,
        "volumeMountPath": "/workspace",
        "containerDiskInGb": args.container_disk_gb,
        "interruptible": bool(args.interruptible),
        "supportPublicIp": True,
    }
    if args.network_volume_id:
        body["networkVolumeId"] = args.network_volume_id
    if args.data_center_id:
        body["dataCenterId"] = args.data_center_id
    return _rest(api_key, "POST", "/pods", body)


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
