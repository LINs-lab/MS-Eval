# Enroot 镜像

[English](README.md) | 简体中文

使用 [Enroot](https://github.com/NVIDIA/enroot) 代替 Docker 构建 MS-Eval 运行环境，适用于没有 root 权限的集群等场景。镜像基于 Ubuntu 22.04，依赖版本与 [Docker 构建](../docker/README.zh-CN.md)一致。

## 环境要求

- Linux **x86-64** 主机，普通用户账号
- [Enroot 3.5+](https://github.com/NVIDIA/enroot/blob/master/doc/installation.md)，并允许创建用户及挂载命名空间。若安装在用户目录，将 `ENROOT_INSTALL_ROOT` 设为包含 `bin/`、`lib/`、`etc/` 的目录。
- 构建：Git、Bash、Python 3.10+、rsync、squashfs-tools；可联网；预留 **50 GB** 本地磁盘和 **16 GB** 内存。临时文件默认写入 `/tmp`，可通过 `TMPDIR` 指定其他本地磁盘。
- 评测：PostgreSQL 15 工具（`initdb`、`pg_ctl`、`pg_isready`、`psql`、`createdb`），以及 curl、iproute2、util-linux、procps、gzip。

Debian 12 可执行：

```bash
sudo apt-get install git python3 rsync squashfs-tools postgresql-15 curl iproute2 util-linux procps gzip
```

## 构建

在仓库根目录执行：

```bash
git clone --recurse-submodules https://github.com/LINs-lab/MS-Eval.git
cd MS-Eval
bash enroot/build.sh
source .local/enroot/env.sh   # 每个运行 benchmark 的 shell 都需加载
```

脚本会导入基础镜像、安装依赖、基于子模块编译 MCP 服务与 Kimi-Code、校验镜像并导出运行包，无需模型 API 密钥。已有仓库请先执行 `git submodule update --init --recursive`，并保持两个子模块位于固定提交。

```text
.local/enroot/                 # Git 忽略；请保留完整目录
├── images/toolathlon-pack.sqsh
├── kimi_dist/kimi-code/       # 由 kimi-code/ 构建的 Kimi-Code CLI
├── overlays/                  # MCP 服务构建产物
├── runtime.json               # 构建信息
└── env.sh                     # 运行环境变量
```

| 参数 | 说明 |
| --- | --- |
| `--output DIR` | 运行包目录（默认 `.local/enroot/`），须为尚不存在的目录 |
| `--base-image FILE` | 使用本地 Ubuntu 22.04 amd64 `.sqsh`，不再下载基础镜像 |
| `--check` | 仅检查构建工具与源码版本，不构建 |

构建失败不会留下不完整的运行包。重新构建时，请通过 `--output` 指定新目录。

## 运行

在[运行指南](../toolathlon_gym/run_sh_eval/README.zh-CN.md)的任一预设中使用 `--backend enroot`：

```bash
bash toolathlon_gym/run_sh_eval/kimi-k3/spec/run.sh --backend enroot
```

每次运行全部 166 个任务。每个并发任务都会在 `/dev/shm` 中创建独立的 rootfs 和数据库，请预留镜像解压后大小加每任务至少 8 GiB 的空间，并从 `MAX_CONCURRENT=1` 开始。结果写入 `results/MODEL/VARIANT/`，可直接用于[计算指标](../eval/README.zh-CN.md)。
