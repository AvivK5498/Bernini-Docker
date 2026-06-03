#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any


GRAPHQL_URL = "https://api.runpod.io/graphql"
REST_BASE = "https://rest.runpod.io/v1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the Bernini Runpod endpoint.")
    parser.add_argument("--image", required=True, help="Docker image, e.g. docker.io/user/bernini-serverless:v0.1.0")
    parser.add_argument("--name", default="Bernini-R - Production")
    parser.add_argument("--template-name", default="bernini-r-serverless")
    parser.add_argument("--gpu", action="append", default=["NVIDIA H200"], help="GPU display name/id; repeatable")
    parser.add_argument("--gpu-count", type=int, default=1)
    parser.add_argument("--workers-min", type=int, default=0)
    parser.add_argument("--workers-max", type=int, default=4)
    parser.add_argument("--idle-timeout", type=int, default=120)
    parser.add_argument("--execution-timeout-ms", type=int, default=7_200_000)
    parser.add_argument("--container-disk-gb", type=int, default=300)
    parser.add_argument("--network-volume-id", default="")
    parser.add_argument("--data-center-id", action="append", default=[])
    parser.add_argument("--runtime-branch", default="main")
    parser.add_argument("--output", default="runpod-endpoint.json")
    args = parser.parse_args()

    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        raise SystemExit("RUNPOD_API_KEY is required")

    template = save_template(
        api_key,
        name=args.template_name,
        image=args.image,
        container_disk_gb=args.container_disk_gb,
        env={
            "BERNINI_RUNTIME_REPO": "https://github.com/AvivK5498/Bernini-Runtime.git",
            "BERNINI_RUNTIME_BRANCH": args.runtime_branch,
            "BERNINI_NUM_GPUS": str(args.gpu_count),
            "BERNINI_MODEL_DIR": "/runpod-volume/models/Bernini-R-Diffusers"
            if args.network_volume_id
            else "/models/Bernini-R-Diffusers",
        },
    )
    endpoint = upsert_endpoint(api_key, args=args, template_id=template["id"])
    result = {"template": template, "endpoint": endpoint}
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


def save_template(api_key: str, *, name: str, image: str, container_disk_gb: int, env: dict[str, str]) -> dict[str, Any]:
    env_pairs = ", ".join(
        f'{{ key: "{_gql_escape(key)}", value: "{_gql_escape(value)}" }}'
        for key, value in env.items()
    )
    query = f"""
mutation {{
  saveTemplate(input: {{
    name: "{_gql_escape(name)}"
    imageName: "{_gql_escape(image)}"
    dockerArgs: ""
    containerDiskInGb: {container_disk_gb}
    volumeInGb: 0
    isServerless: true
    env: [{env_pairs}]
  }}) {{
    id
    name
    imageName
  }}
}}
""".strip()
    data = _graphql(api_key, query)
    template = data.get("saveTemplate") or {}
    if not template.get("id"):
        raise RuntimeError(f"saveTemplate returned no id: {data}")
    return template


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
        "flashboot": True,
        "minCudaVersion": "12.8",
    }
    if args.network_volume_id:
        body["networkVolumeId"] = args.network_volume_id
    if args.data_center_id:
        body["dataCenterIds"] = args.data_center_id

    if existing:
        endpoint = _rest(api_key, "PATCH", f"/endpoints/{existing['id']}", body)
    else:
        endpoint = _rest(api_key, "POST", "/endpoints", body)
    return endpoint


def _graphql(api_key: str, query: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{GRAPHQL_URL}?api_key={api_key}",
        data=json.dumps({"query": query}).encode(),
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        body = json.loads(response.read())
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body.get("data") or {}


def _rest(api_key: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{REST_BASE}{path}",
        data=data,
        method=method,
        headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            text = response.read().decode()
    except Exception as exc:
        if hasattr(exc, "read"):
            detail = exc.read().decode(errors="replace")[:1200]
            raise RuntimeError(f"{method} {path} failed: {exc}; {detail}") from exc
        raise
    return json.loads(text) if text else {}


def _gql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

