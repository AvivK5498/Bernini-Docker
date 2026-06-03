#!/usr/bin/env bash
set -euo pipefail

repo_dir="${BERNINI_RUNTIME_DIR:-/opt/bernini-runtime}"
repo_url="${BERNINI_RUNTIME_REPO:-https://github.com/AvivK5498/Bernini-Runtime.git}"
branch="${BERNINI_RUNTIME_BRANCH:-main}"

if [ -d "$repo_dir/.git" ]; then
  git -C "$repo_dir" fetch --depth=1 origin "$branch"
  git -C "$repo_dir" reset --hard "origin/$branch"
else
  rm -rf "$repo_dir"
  git clone --depth=1 --branch "$branch" "$repo_url" "$repo_dir"
fi

pip install -e "$repo_dir"

python /opt/prefetch_model.py
exec python -m bernini_runtime.handler

