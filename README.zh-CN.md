<div align="center">

# MS-Eval

**Benchmarking Sub-Agent Delegation and Orchestration in MCP-Intensive Working Scenarios**

[![arXiv](https://img.shields.io/badge/arXiv-2610.22869-b31b1b.svg)](https://arxiv.org/abs/2610.22869)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | 简体中文

</div>

MS-Eval 评测前沿大模型在 **主 Agent 委派、子 Agent 执行（Main-Agent Delegation and Sub-Agent Execution，MAD-SAE）** 范式下的表现：主 Agent 拆解任务，并把子任务委派给子 Agent 执行（如 Kimi-Code 的 AgentSwarm、Cursor 的 MultiTask 模式、Claude Code 的子 Agent 编排）。评测聚焦 **MCP 密集型工作场景**，从两个互补的角度展开：

- **委派适当性（Delegation Appropriateness，DA）：** 主 Agent 是否在该委派时委派、委派方式是否合理？
- **编排效用（Orchestration Utilities，OU）：** 与单 Agent（SA）基线相比，子 Agent 编排能否提升性能、效率并降低成本？

DA 与 OU 合成为单一指标 **MAD-SAE Quality（MSQ）**：以委派适当性对平均效用进行折算。

<p align="center">
  <img src="assets/case_visualize/paradigms_compare/deepseek-v4-flash-0731/mse-kit.png" width="720" alt="MS-Eval Kit 概览">
  <br>
  <em><b>MS-Eval Kit 概览。</b><b>Benchmark</b>：以任务 <code>arxiv-survey-presentation</code> 为例，展示任务描述及其委派先验（3 个波次、9 个子 Agent）。<b>Harness</b>：各执行范式共用的行为准则与工具权限。<b>Eval Metrics</b>：MAD-SAE 指标的计算方式。</em>
</p>

| 组成部分            | 说明                                                                                                                                                                                                                                                                                                       |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Benchmark** | 来自 Toolathlon-Gym 的 166 个任务，覆盖 8 类真实工作场景。每个任务配有*委派先验（Delegation Prior）*：一份金标准方案，规定*何时*委派、使用*哪些*类型的子 Agent、各自负责*哪些*子任务。其中 89 个任务需要委派（$\mathcal{D}_{\text{need}}$），77 个无需委派（$\mathcal{D}_{\text{no-need}}$）。 |
| **Harness**   | 基于原生支持子 Agent 的 Kimi-Code 构建 MAD-SAE 与 SA 两种范式。禁用内置 skills，并固定系统提示词与工具权限，确保两者仅在范式上不同。                                                                                                                                                                       |
| **Metrics**   | DA、OU 与 MSQ，定义见下文。                                                                                                                                                                                                                                                                                |
| **运行环境**  | 同一套锁定的依赖，提供 **Docker** 镜像和 **Enroot** 镜像两种方案，后者适用于无 root 权限的集群。每个任务在独立容器中运行，并使用全新的数据库。                                                                                                                                                 |

<a id="metrics"></a>

## 📊 评测指标

**委派适当性（DA）** 衡量主 Agent 是否委派、如何委派。

| 指标                          | 含义                                          | 定义                                                                                                                      |
| :---------------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **UDR ↓**              | 应委派却未委派                                | $\frac{\lvert\mathcal{D}_{\text{need}}\setminus\mathcal{D}_{\text{del}}\rvert}{\lvert\mathcal{D}_{\text{need}}\rvert}$  |
| **ODR ↓**              | 不必委派却委派                                | $\frac{\lvert\mathcal{D}_{\text{no-need}}\cap\mathcal{D}_{\text{del}}\rvert}{\lvert\mathcal{D}_{\text{no-need}}\rvert}$ |
| **P<sub>hit</sub> ↑**  | 实际子 Agent 单元的精确率                     | $\frac{\sum_t m_t}{\sum_t\lvert E_t\rvert}$                                                                             |
| **R<sub>hit</sub> ↑**  | 金标准子 Agent 单元的召回率                   | $\frac{\sum_t m_t}{\sum_t\lvert G_t\rvert}$                                                                             |
| **F1<sub>hit</sub> ↑** | P<sub>hit</sub> 与 R<sub>hit</sub> 的调和平均 | $\frac{2P_{\text{hit}}R_{\text{hit}}}{P_{\text{hit}}+R_{\text{hit}}}$                                                   |

**编排效用（OU）** 将 MAD-SAE 与 SA 基线对比。各效用取值范围为 0 到 1，**0.5 表示持平**，越高越好。

| 指标                       | 含义     | 定义                                                                                       | 任务集合                         |
| :------------------------- | :------- | :----------------------------------------------------------------------------------------- | :------------------------------- |
| **U<sub>p</sub> ↑** | 性能效用 | $\frac{\text{SR}_{\text{mad}}}{\text{SR}_{\text{mad}}+\text{SR}_{\text{sa}}}$            | $\mathcal{D}_{\text{del}}$     |
| **U<sub>e</sub> ↑** | 效率效用 | $\frac{\text{Csteps}_{\text{sa}}}{\text{Csteps}_{\text{mad}}+\text{Csteps}_{\text{sa}}}$ | $\mathcal{D}_{\text{del}}^{+}$ |
| **U<sub>c</sub> ↑** | 成本效用 | $\frac{\text{Cost}_{\text{sa}}}{\text{Cost}_{\text{mad}}+\text{Cost}_{\text{sa}}}$       | $\mathcal{D}_{\text{del}}^{+}$ |

**MAD-SAE Quality（MSQ）↑** 综合二者，三项效用等权：

$$
\mathrm{MSQ}=F1_{\text{hit}}\cdot\frac{U_p+U_e+U_c}{3}
$$

- $\mathcal{D}_{\text{del}}$：主 Agent 至少调用了一个非规划子 Agent 的任务。$\mathcal{D}_{\text{del}}^{+}$：其中成功完成的子集，因为效率与成本只对已解决的任务有意义。
- 命中指标：由 LLM 审核模型按功能为金标准与实际子 Agent 打标签，按波次（wave）组成功能单元，再通过最大二分匹配一对一配对。$G_t$、$E_t$ 分别为任务 $t$ 的金标准与实际单元，$m_t$ 为匹配数。

<a id="results"></a>

## 🏆 实验结果

<p align="center">
  <img src="assets/msq_ranking_MSE_Kit.png" width="800" alt="MSQ 排名">
</p>

8 个前沿模型在专家子 Agent 模式（Spec）下的 MSQ（%），以及 DeepSeek-V4-Flash-0731 在通用子 Agent 模式（Gen）下单独运行、结合先规划（Plan-1st）或 oracle 任务说明（Oracle）时的 MSQ。逐任务 DA 结果见 [`eval/eval_results`](eval/eval_results/README.zh-CN.md)。

<a id="quick-start"></a>

## 🚀 快速开始

MS-Eval 提供两种可互换的镜像方案，基于同一套锁定的依赖构建：**Docker** 镜像（也可使用 Podman）适用于工作站和服务器，**Enroot** 镜像适用于没有 root 权限的 HPC 集群。需要 Linux x86-64 主机、Python 3.10+、40–50 GB 可用磁盘空间，以及被测模型的 API 密钥。

### 1. 构建运行环境

```bash
git clone --recurse-submodules https://github.com/LINs-lab/MS-Eval.git
cd MS-Eval
```

然后任选一种方案构建，均不需要模型 API 密钥。

**方案 A：Docker**（工作站和服务器；[构建指南](docker/README.zh-CN.md)）

```bash
bash docker/build.sh            # 构建 ms-eval:local 和 ms-eval-db:local 两个镜像
```

**方案 B：Enroot**（无 root 权限的集群；[构建指南](enroot/README.zh-CN.md)）

```bash
bash enroot/build.sh            # 将运行环境输出到 .local/enroot/
source .local/enroot/env.sh     # 每个运行 benchmark 的 shell 都需先执行
```

### 2. 运行 benchmark

使用相同配置运行同一模型两次：专家子 Agent 模式（`spec`）与单 Agent 基线（`sa`）。

```bash
MODEL=kimi-k3                        # toolathlon_gym/run_sh_eval/ 下的任一模型目录
BACKEND=docker                       # 或 enroot
P=toolathlon_gym/run_sh_eval/$MODEL
cp $P/spec/config.env.example $P/spec/config.env   # 填写 API_BASE_URL 和 API_KEY
cp $P/spec/config.env $P/sa/config.env

bash $P/spec/run.sh --backend $BACKEND --dry-run   # 检查配置，不调用 API
bash $P/spec/run.sh --backend $BACKEND             # MAD-SAE，166 个任务
bash $P/sa/run.sh --backend $BACKEND               # SA 基线，166 个任务
```

结果保存在 `results/$MODEL/spec/` 和 `results/$MODEL/sa/` 下。使用 Docker 时，可加 `--task canvas-course-comparison` 先试跑一个任务。其他模式与参数见[运行指南](https://github.com/Danield21/toolathlon_gym/blob/main/run_sh_eval/README.zh-CN.md)。

### 3. 计算指标

```bash
python3 -m eval.common.build_audit_summary results/$MODEL/spec results/$MODEL/sa

export DELEGATE_LLM_API_KEY=...      # 为子 Agent 打功能标签的 LLM 审核模型
python3 -m eval.delegation_appropriateness.evaluate \
  --dump results/$MODEL/spec --out results/$MODEL/spec --match

python3 -m eval.summarize --root results > results/metrics.md
```

`results/metrics.md` 汇总 `results/` 下所有模型的 DA、OU 与 MSQ。参数与输出格式见[评测指南](eval/README.zh-CN.md)。

## 📁 目录结构

| 目录                                                                       | 内容                                       |
| -------------------------------------------------------------------------- | ------------------------------------------ |
| [`data/`](data/README.zh-CN.md)                                           | 166 个任务文档及任务分类                   |
| [`eval/`](eval/README.zh-CN.md)                                           | DA / OU / MSQ 评测器与已发布结果           |
| [`docker/`](docker/README.zh-CN.md)、[`enroot/`](enroot/README.zh-CN.md) | Docker 与 Enroot 两种运行环境的构建        |
| [`toolathlon_gym/`](https://github.com/Danield21/toolathlon_gym/blob/main/run_sh_eval/README.zh-CN.md)           | 子模块：benchmark 环境、MCP 服务与启动脚本 |
| [`kimi-code/`](https://github.com/Danield21/kimi-code/tree/tool-result-persistence-fix) | 子模块：Kimi-Code Agent 框架               |
| [`visualize_script/`](visualize_script/README.zh-CN.md)                   | 论文图表绘制脚本                           |
| `assets/`                                                                | 图片与案例可视化                           |
| `results/`                                                               | 运行结果与报告（Git 忽略）                 |

## 🙏 致谢

MS-Eval 基于以下两个开源项目构建，感谢其作者的开源贡献。

- **[Kimi-Code](https://github.com/MoonshotAI/kimi-code)**（Moonshot AI，MIT 许可证）：我们的 Harness 基于它构建，MAD-SAE 与 SA 两种范式均在其上运行。我们使用其开发版本 [`0b2e803d`](https://github.com/MoonshotAI/kimi-code/commit/0b2e803d5e71afaab45212bb2ee6117ecbf8bbc9)（2026-08-07，v0.34.0 之后），并加入一个补丁：将超长的工具输出保存在任务工作区内。
- **[Toolathlon-Gym](https://github.com/eigent-ai/toolathlon_gym)**（Eigent AI，Apache License 2.0）：在 HKUST-NLP 的 [Toolathlon](https://github.com/hkust-nlp/Toolathlon) 基础上扩展而来，提供任务、MCP server 与数据库。我们以其开发版本 [`45bbff8`](https://github.com/eigent-ai/toolathlon_gym/commit/45bbff81419fedbb6d5a2cb46029d2980a7c93c4)（2026-07-22）为起点，针对 MS-Eval 的 166 个任务做了修订：

  - **题目要求**：澄清了 120 个任务的任务说明；
  - **Checklist 口径**：修订了 150 个任务的评分检查项，以及 61 个任务的初始状态或参考答案；
  - **MCP server**：修复并加固了 14 个 MCP server。

修改后的两个版本即本仓库的两个子模块，`git clone --recurse-submodules` 会检出我们评测时使用的确切提交。如需单独使用，请选择以下分支：

| 子模块 | 仓库 | 分支 |
| --- | --- | --- |
| `kimi-code/` | [Danield21/kimi-code](https://github.com/Danield21/kimi-code/tree/tool-result-persistence-fix) | **`tool-result-persistence-fix`**（不要用 `main`：它是较早的上游快照，不含我们的补丁） |
| `toolathlon_gym/` | [Danield21/toolathlon_gym](https://github.com/Danield21/toolathlon_gym) | **`main`** |

## 📝 引用

```bibtex
@misc{ding2026msevalbenchmarkingsubagentdelegation,
      title={MS-Eval: Benchmarking Sub-Agent Delegation and Orchestration in MCP-Intensive Working Scenarios}, 
      author={Bowen Ding and Qixin Wang and Lexing Ruan and Weiyi Lu and Qiwei Ge and Ruishan Fang and Tao Lin},
      year={2026},
      eprint={2610.22869},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2610.22869}, 
}
```

## 📄 许可证

MS-Eval 基于 [MIT License](LICENSE) 发布。
