# Docker 镜像

[English](README.md) | 简体中文

构建使用 Docker 运行 MS-Eval 所需的两个镜像。

| 镜像 | 内容 |
| --- | --- |
| `ms-eval:local` | 评测运行环境、MCP 服务与 Kimi-Code CLI |
| `ms-eval-db:local` | 含任务数据的 PostgreSQL |

## 环境要求

- Linux **x86-64** 主机，当前账号可使用 Docker Engine
- Git、Bash、Python 3.10+
- 可联网，预留约 **40 GB** 磁盘和 **16 GB** 内存

## 构建

在仓库根目录执行：

```bash
git clone --recurse-submodules https://github.com/LINs-lab/MS-Eval.git
cd MS-Eval
bash docker/build.sh
```

脚本会构建两个镜像并校验运行环境，无需模型 API 密钥。构建中断后重新执行同一命令，即可复用已缓存的镜像层。

- **已有仓库：** 先执行 `git submodule update --init --recursive`。两个子模块须保持在固定提交，不要使用 `--remote`，也不要做本地修改，否则构建会拒绝执行。依赖版本固定在 [`locks/`](locks/) 中。
- **可选设置：** 设置 `CONTAINER_ENGINE=podman` 可改用 Podman；设置 `MSE_IMAGE` / `MSE_DB_IMAGE` 可修改镜像标签。

下一步：[运行 benchmark](../README.zh-CN.md#quick-start)。
