#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit and poll a Bernini Runpod job.")
    parser.add_argument("--endpoint-id", required=True)
    parser.add_argument("--payload", required=True, help="JSON payload file containing the Runpod input object or full envelope")
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--output", default="runpod-job-result.json")
    args = parser.parse_args()

    api_key = os.environ.get("RUNPOD_API_KEY")
    if not api_key:
        raise SystemExit("RUNPOD_API_KEY is required")

    raw = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    envelope = raw if "input" in raw else {"input": raw}
    submitted = _post(api_key, args.endpoint_id, "run", envelope)
    job_id = submitted["id"]
    print(json.dumps({"submitted": submitted}, indent=2), flush=True)

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        status = _post(api_key, args.endpoint_id, f"status/{job_id}", None)
        print(json.dumps({"status": status.get("status"), "delayTime": status.get("delayTime"), "executionTime": status.get("executionTime")}), flush=True)
        if status.get("status") in {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}:
            Path(args.output).write_text(json.dumps(status, indent=2), encoding="utf-8")
            print(json.dumps(status, indent=2))
            if status.get("status") != "COMPLETED":
                raise SystemExit(1)
            return
        time.sleep(args.poll_interval)
    raise SystemExit(f"Timed out waiting for job {job_id}")


def _post(api_key: str, endpoint_id: str, action: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"https://api.runpod.ai/v2/{endpoint_id}/{action}",
        data=data,
        method="POST",
        headers={"authorization": f"Bearer {api_key}", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read())


if __name__ == "__main__":
    main()

