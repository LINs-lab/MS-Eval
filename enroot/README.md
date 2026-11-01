# Enroot Image

English | [简体中文](README.zh-CN.md)

Build the MS-Eval runtime with [Enroot](https://github.com/NVIDIA/enroot) instead of Docker, e.g. on clusters without root access. The image is built from Ubuntu 22.04 with the same pinned dependencies as the [Docker build](../docker/README.md).

## Requirements

- Linux **x86-64** host, regular user account
- [Enroot 3.5+](https://github.com/NVIDIA/enroot/blob/master/doc/installation.md), with user and mount namespaces enabled. For a user installation, set `ENROOT_INSTALL_ROOT` to the directory containing `bin/`, `lib/`, and `etc/`.
- Build: Git, Bash, Python 3.10+, rsync, squashfs-tools; internet access; **50 GB** of local disk and **16 GB** of RAM. Temporary files go to `/tmp`; set `TMPDIR` to use another local disk.
- Evaluation: PostgreSQL 15 client and server tools (`initdb`, `pg_ctl`, `pg_isready`, `psql`, `createdb`), curl, iproute2, util-linux, procps, gzip.

On Debian 12:

```bash
sudo apt-get install git python3 rsync squashfs-tools postgresql-15 curl iproute2 util-linux procps gzip
```

## Build

Run from the repository root:

```bash
git clone --recurse-submodules https://github.com/LINs-lab/MS-Eval.git
cd MS-Eval
bash enroot/build.sh
source .local/enroot/env.sh   # load in every shell that runs the benchmark
```

The script imports the base image, installs dependencies, builds the MCP servers and Kimi-Code from the submodules, verifies the image, and exports the runtime bundle. No model API key is needed. For an existing clone, run `git submodule update --init --recursive` first and keep both submodules at their pinned commits.

```text
.local/enroot/                 # git-ignored; keep the whole directory
├── images/toolathlon-pack.sqsh
├── kimi_dist/kimi-code/       # Kimi-Code CLI built from kimi-code/
├── overlays/                  # MCP server builds
├── runtime.json               # Build metadata
└── env.sh                     # Runtime environment
```

| Option | Description |
| --- | --- |
| `--output DIR` | Bundle directory (default: `.local/enroot/`); must not exist yet |
| `--base-image FILE` | Use a local Ubuntu 22.04 amd64 `.sqsh` instead of downloading one |
| `--check` | Check tools and source versions without building |

A failed build leaves no partial bundle. To rebuild, pass a new `--output` directory.

## Run

Use `--backend enroot` with any preset in the [run guide](../toolathlon_gym/run_sh_eval/README.md):

```bash
bash toolathlon_gym/run_sh_eval/kimi-k3/spec/run.sh --backend enroot
```

Each invocation runs all 166 tasks. Every concurrent task gets its own rootfs and database in `/dev/shm`, so reserve the unpacked image size plus at least 8 GiB per task, and start with `MAX_CONCURRENT=1`. Results go to `results/MODEL/VARIANT/`, ready for [computing metrics](../eval/README.md).
