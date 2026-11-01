# Docker Images

English | [简体中文](README.zh-CN.md)

Build the two images used to run MS-Eval with Docker.

| Image | Contents |
| --- | --- |
| `ms-eval:local` | Evaluation runtime, MCP servers, and the Kimi-Code CLI |
| `ms-eval-db:local` | PostgreSQL with the task data |

## Requirements

- Linux **x86-64** host with Docker Engine usable by your account
- Git, Bash, Python 3.10+
- Internet access, about **40 GB** of disk and **16 GB** of RAM

## Build

Run from the repository root:

```bash
git clone --recurse-submodules https://github.com/LINs-lab/MS-Eval.git
cd MS-Eval
bash docker/build.sh
```

The script builds both images and verifies the runtime. No model API key is needed. If the build is interrupted, rerun the same command to reuse cached layers.

- **Existing clone:** run `git submodule update --init --recursive` first. Keep both submodules at their pinned commits, without `--remote` or local edits; the build refuses other revisions. Dependency versions are pinned in [`locks/`](locks/).
- **Options:** set `CONTAINER_ENGINE=podman` to use Podman, or `MSE_IMAGE` / `MSE_DB_IMAGE` to change image tags.

Next: [run the benchmark](../README.md#2-run-the-benchmark).
