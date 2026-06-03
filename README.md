# Bernini Docker

Runpod serverless Docker image for [ByteDance/Bernini-R](https://huggingface.co/ByteDance/Bernini-R).

The image contains heavy, persistent dependencies:

- CUDA 12.8 runtime/devel base
- Python 3.12 virtualenv
- torch 2.8 CUDA 12.8 wheels
- FlashAttention 2.8.3 prebuilt wheel for `linux_x86_64`
- upstream `bytedance/Bernini`
- Runpod serverless SDK

Mutable endpoint behavior lives in
[`AvivK5498/Bernini-Runtime`](https://github.com/AvivK5498/Bernini-Runtime).
The container fetches that repo at startup.

CircleCI publishes the image to Docker Hub as:

```text
docker.io/$DOCKERHUB_USER/bernini-serverless:<tag>
```

