from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    model_dir = Path(os.environ.get("BERNINI_MODEL_DIR", "/runpod-volume/models/Bernini-R-Diffusers"))
    if (model_dir / "model_index.json").exists():
        print(f"Bernini model already present: {model_dir}", flush=True)
        return
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading ByteDance/Bernini-R-Diffusers to {model_dir}", flush=True)
    snapshot_download(
        repo_id="ByteDance/Bernini-R-Diffusers",
        local_dir=str(model_dir),
        local_dir_use_symlinks=False,
        resume_download=True,
    )


if __name__ == "__main__":
    main()

