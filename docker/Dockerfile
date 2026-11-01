# Build from the MS-Eval root with: bash docker/build.sh
# Source and Python pins are recorded in docker/locks/reference.json.
ARG BASE_IMAGE=docker.io/library/ubuntu:22.04
ARG KIMI_BUILD_IMAGE=docker.io/library/node:24.15.0-bookworm
ARG POSTGRES_IMAGE=docker.io/library/postgres:15-bookworm

FROM ${KIMI_BUILD_IMAGE} AS kimi-builder
ARG NPM_REGISTRY=https://registry.npmjs.org
ENV npm_config_registry=${NPM_REGISTRY} \
    CI=true SKIP_INSTALL_SIMPLE_GIT_HOOKS=1 PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
WORKDIR /src/kimi-code
COPY kimi-code/ ./
RUN npm install --global pnpm@10.33.0 \
    && pnpm install --frozen-lockfile \
    && pnpm run build:packages \
    && pnpm --filter @moonshot-ai/kimi-code run build \
    && test -s apps/kimi-code/dist/main.mjs

FROM ${POSTGRES_IMAGE} AS database
RUN apt-get update && apt-get install -y --no-install-recommends iptables util-linux \
    && rm -rf /var/lib/apt/lists/*
COPY toolathlon_gym/db/init.sql.gz /docker-entrypoint-initdb.d/10-fixture.sql.gz
COPY docker/database-fix.sql /docker-entrypoint-initdb.d/20-fixes.sql
COPY docker/database-entrypoint.sh /usr/local/bin/mse-database
ARG DATABASE_SEED_SHA256=unknown
LABEL org.ms-eval.database-seed-sha256=${DATABASE_SEED_SHA256}
ENV TZ=UTC PGTZ=UTC
ENTRYPOINT ["bash", "/usr/local/bin/mse-database"]
CMD ["postgres", "-c", "listen_addresses=127.0.0.1", "-c", "timezone=UTC", "-c", "max_connections=40", "-c", "fsync=off", "-c", "synchronous_commit=off"]

FROM ${BASE_IMAGE} AS evaluator
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
ARG DEBIAN_FRONTEND=noninteractive
ARG NPM_REGISTRY=https://registry.npmjs.org
ARG NODE_MIRROR=https://nodejs.org/dist
ARG UV_INDEX_URL=https://pypi.org/simple
ARG UV_PYTHON_INSTALL_MIRROR
ARG PLAYWRIGHT_DOWNLOAD_HOST
ARG GYM_COMMIT=unknown
ARG KIMI_COMMIT=unknown
LABEL org.opencontainers.image.title="MS-Eval" \
      org.opencontainers.image.source="https://github.com/LINs-lab/MS-Eval" \
      org.ms-eval.gym-commit=${GYM_COMMIT} org.ms-eval.kimi-commit=${KIMI_COMMIT}
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git xz-utils python3 python3-pip python3-venv \
      build-essential pkg-config libffi-dev libssl-dev libseccomp2 bubblewrap \
      postgresql-client rsync lsof psmisc procps iproute2 util-linux \
      poppler-utils qpdf fonts-liberation fonts-noto-cjk \
      zip unzip file tree tini \
    && rm -rf /var/lib/apt/lists/*
COPY docker/locks /opt/ms-eval/locks
COPY docker/install-runtime.py /opt/ms-eval/install-runtime.py
RUN python3 /opt/ms-eval/install-runtime.py bootstrap
ENV UV_PYTHON_INSTALL_DIR=/opt/uv_python_cache \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
COPY toolathlon_gym/local_servers/ /opt/local_servers/
RUN python3 /opt/ms-eval/install-runtime.py dependencies
RUN apt-get update \
    && /opt/venv/bin/playwright install-deps chromium \
    && /opt/venv/bin/playwright install chromium \
    && cd /opt/local_servers/playwright-mcp \
    && node node_modules/playwright/cli.js install chromium \
    && rm -rf /var/lib/apt/lists/*
COPY --from=kimi-builder /src/kimi-code/apps/kimi-code/dist /opt/kimi-code/dist
COPY --from=kimi-builder /src/kimi-code/apps/kimi-code/dist-web /opt/kimi-code/dist-web
COPY --from=kimi-builder /src/kimi-code/apps/kimi-code/native /opt/kimi-code/native
COPY --from=kimi-builder /src/kimi-code/apps/kimi-code/package.json /opt/kimi-code/package.json
COPY toolathlon_gym/ /workspace/
COPY data/oracle166/ /workspace/tasks/oracle166/
COPY toolathlon_gym/run_sh_eval/docker/gateway.py toolathlon_gym/run_sh_eval/docker/task-entry.py toolathlon_gym/run_sh_eval/docker/smoke.py /opt/ms-eval/
COPY docker/verify-image.py /opt/ms-eval/
RUN mkdir -p /workspace/scripts /workspace/dumps \
    && printf '#!/bin/sh\nexec /usr/local/bin/node /opt/kimi-code/dist/main.mjs "$@"\n' > /usr/local/bin/kimi \
    && chmod +x /usr/local/bin/kimi \
    && printf '%s\n' '{"gym":"'"$GYM_COMMIT"'","kimi":"'"$KIMI_COMMIT"'"}' > /opt/ms-eval/source-commits.json
ENV VIRTUAL_ENV=/opt/venv LOCAL_SERVERS_PATH=/opt/local_servers \
    PYTHON_BIN=/opt/venv/bin/python3 HOME=/root TZ=UTC PGTZ=UTC \
    UV_NO_SYNC=true UV_OFFLINE=true UV_FROZEN=true \
    KIMI_CODE_BUILTIN_PRODUCT_SKILLS=0 PLAYWRIGHT_MCP_SANDBOX=false
WORKDIR /workspace
RUN /opt/venv/bin/python /opt/ms-eval/verify-image.py
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash"]
