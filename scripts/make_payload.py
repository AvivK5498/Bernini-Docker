#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Bernini v2v payload JSON.")
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default="payload.json")
    parser.add_argument("--num-frames", type=int, default=33)
    parser.add_argument("--fps", type=int, default=16)
    parser.add_argument("--max-image-size", type=int, default=848)
    parser.add_argument("--num-gpus", type=int, default=1)
    args = parser.parse_args()

    payload = {
        "task_type": "v2v",
        "guidance_mode": "v2v_apg",
        "prompt": args.prompt,
        "video_url": args.video_url,
        "num_frames": args.num_frames,
        "fps": args.fps,
        "max_image_size": args.max_image_size,
        "num_gpus": args.num_gpus,
        "seed": 42,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

