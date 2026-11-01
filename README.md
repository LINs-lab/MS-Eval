<div align="center">

# MS-Eval

**Benchmarking Sub-Agent Delegation and Orchestration in MCP-Intensive Working Scenarios**

[![arXiv](https://img.shields.io/badge/arXiv-2610.22869-b31b1b.svg)](https://arxiv.org/abs/2610.22869)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

English | [简体中文](README.zh-CN.md)

</div>

MS-Eval evaluates frontier LLMs under the **Main-Agent Delegation and Sub-Agent Execution (MAD-SAE)** paradigm, in which a main agent decomposes a task and delegates sub-tasks to sub-agents (e.g., AgentSwarm in Kimi-Code, MultiTask mode in Cursor, sub-agent orchestration in Claude Code), in **MCP-intensive working scenarios**. It examines two complementary perspectives:

- **Delegation Appropriateness (DA):** Does the main agent delegate *when* and *how* it should?
- **Orchestration Utilities (OU):** Compared with a single-agent (SA) baseline, does orchestration improve performance, efficiency, and cost?

DA and OU are combined into a single index, **MAD-SAE Quality (MSQ)**: the average utility discounted by delegation appropriateness.

<p align="center">
  <img src="assets/case_visualize/paradigms_compare/deepseek-v4-flash-0731/mse-kit.png" width="720" alt="Overview of MS-Eval Kit">
  <br>
  <em><b>Overview of MS-Eval Kit.</b> <b>Benchmark</b>: task <code>arxiv-survey-presentation</code> with its Task Description and Delegation Prior (3 waves, 9 sub-agents). <b>Harness</b>: principles and tool permissions shared by all execution paradigms. <b>Eval Metrics</b>: how the MAD-SAE metrics are computed.</em>
</p>

| Component           | Description                                                                                                                                                                                                                                                                                                                         |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Benchmark** | 166 tasks from Toolathlon-Gym across 8 real-world working scenarios. Each task has a *Delegation Prior*: a golden plan of *when* to delegate, *which* sub-agent types to use, and *which* sub-tasks they handle. 89 tasks need delegation ($\mathcal{D}_{\text{need}}$) and 77 do not ($\mathcal{D}_{\text{no-need}}$). |
| **Harness**   | MAD-SAE and SA paradigms built on Kimi-Code, which supports sub-agents natively. Built-in skills are disabled, and the system prompt and tool access are fixed, so only the paradigm differs.                                                                                                                                       |
| **Metrics**   | DA, OU, and MSQ, defined below.                                                                                                                                                                                                                                                                                                     |
| **Runtime**   | One pinned environment, shipped as **Docker** images or an **Enroot** image for clusters without root access. Each task runs in its own container with a fresh database.                                                                                                                                                |

<a id="metrics"></a>

## 📊 Metrics

**Delegation Appropriateness (DA)** measures whether and how the main agent delegates.

| Metric                        | Meaning                                              | Definition                                                                                                                |
| :---------------------------- | :--------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **UDR ↓**              | Needed delegation was skipped                        | $\frac{\lvert\mathcal{D}_{\text{need}}\setminus\mathcal{D}_{\text{del}}\rvert}{\lvert\mathcal{D}_{\text{need}}\rvert}$  |
| **ODR ↓**              | Unnecessary delegation occurred                      | $\frac{\lvert\mathcal{D}_{\text{no-need}}\cap\mathcal{D}_{\text{del}}\rvert}{\lvert\mathcal{D}_{\text{no-need}}\rvert}$ |
| **P<sub>hit</sub> ↑**  | Precision of executed sub-agent units                | $\frac{\sum_t m_t}{\sum_t\lvert E_t\rvert}$                                                                             |
| **R<sub>hit</sub> ↑**  | Recall of golden sub-agent units                     | $\frac{\sum_t m_t}{\sum_t\lvert G_t\rvert}$                                                                             |
| **F1<sub>hit</sub> ↑** | Harmonic mean of P<sub>hit</sub> and R<sub>hit</sub> | $\frac{2P_{\text{hit}}R_{\text{hit}}}{P_{\text{hit}}+R_{\text{hit}}}$                                                   |

**Orchestration Utilities (OU)** compare MAD-SAE with the SA baseline. Each ranges from 0 to 1; **0.5 means parity**, and higher is better.

| Metric                     | Meaning             | Definition                                                                                 | Tasks                            |
| :------------------------- | :------------------ | :----------------------------------------------------------------------------------------- | :------------------------------- |
| **U<sub>p</sub> ↑** | Performance utility | $\frac{\text{SR}_{\text{mad}}}{\text{SR}_{\text{mad}}+\text{SR}_{\text{sa}}}$            | $\mathcal{D}_{\text{del}}$     |
| **U<sub>e</sub> ↑** | Efficiency utility  | $\frac{\text{Csteps}_{\text{sa}}}{\text{Csteps}_{\text{mad}}+\text{Csteps}_{\text{sa}}}$ | $\mathcal{D}_{\text{del}}^{+}$ |
| **U<sub>c</sub> ↑** | Cost utility        | $\frac{\text{Cost}_{\text{sa}}}{\text{Cost}_{\text{mad}}+\text{Cost}_{\text{sa}}}$       | $\mathcal{D}_{\text{del}}^{+}$ |

**MAD-SAE Quality (MSQ) ↑** combines both, with equal utility weights:

$$
\mathrm{MSQ}=F1_{\text{hit}}\cdot\frac{U_p+U_e+U_c}{3}
$$

- $\mathcal{D}_{\text{del}}$: tasks where the main agent invokes at least one non-planning sub-agent. $\mathcal{D}_{\text{del}}^{+}$: its successfully completed subset, since efficiency and cost only matter for solved tasks.
- Hit scores: an LLM reviewer tags golden and executed sub-agents by function; tags are grouped into per-wave units and matched one-to-one by maximum bipartite matching. $G_t$ and $E_t$ are the golden and executed units of task $t$; $m_t$ is the number of matches.

<a id="results"></a>

## 🏆 Results

<p align="center">
  <img src="assets/msq_ranking_MSE_Kit.png" width="800" alt="MSQ ranking">
</p>

MSQ (%) of 8 frontier models with specialist sub-agents (Spec), plus DeepSeek-V4-Flash-0731 with generalist sub-agents (Gen), alone or with plan-first (Plan-1st) or oracle task briefs (Oracle). Per-task DA results: [`eval/eval_results`](eval/eval_results/README.md).

<a id="quick-start"></a>

## 🚀 Quick Start

MS-Eval supports two interchangeable runtimes built from the same pinned dependencies: **Docker** images (Podman also works) for workstations and servers, and an **Enroot** image for HPC clusters without root access. You need a Linux x86-64 host, Python 3.10+, 40–50 GB of free disk, and an API key for the model under test.

### 1. Build the environment

```bash
git clone --recurse-submodules https://github.com/LINs-lab/MS-Eval.git
cd MS-Eval
```

Then build either runtime. Neither build needs a model API key.

**Option A: Docker** (workstations and servers; [guide](docker/README.md))

```bash
bash docker/build.sh            # builds the ms-eval:local and ms-eval-db:local images
```

**Option B: Enroot** (clusters without root access; [guide](enroot/README.md))

```bash
bash enroot/build.sh            # writes the runtime bundle to .local/enroot/
source .local/enroot/env.sh     # in every shell that runs the benchmark
```

### 2. Run the benchmark

Run a model twice with identical settings: with specialist sub-agents (`spec`) and as the single-agent baseline (`sa`).

```bash
MODEL=kimi-k3                        # any directory in toolathlon_gym/run_sh_eval/
BACKEND=docker                       # or enroot
P=toolathlon_gym/run_sh_eval/$MODEL
cp $P/spec/config.env.example $P/spec/config.env   # set API_BASE_URL and API_KEY
cp $P/spec/config.env $P/sa/config.env

bash $P/spec/run.sh --backend $BACKEND --dry-run   # check settings, no API calls
bash $P/spec/run.sh --backend $BACKEND             # MAD-SAE, 166 tasks
bash $P/sa/run.sh --backend $BACKEND               # SA baseline, 166 tasks
```

Results are saved under `results/$MODEL/spec/` and `results/$MODEL/sa/`. With Docker, you can try one task first by adding `--task canvas-course-comparison`. Other modes and options: [run guide](toolathlon_gym/run_sh_eval/README.md).

### 3. Compute metrics

```bash
python3 -m eval.common.build_audit_summary results/$MODEL/spec results/$MODEL/sa

export DELEGATE_LLM_API_KEY=...      # LLM reviewer that labels sub-agents
python3 -m eval.delegation_appropriateness.evaluate \
  --dump results/$MODEL/spec --out results/$MODEL/spec --match

python3 -m eval.summarize --root results > results/metrics.md
```

`results/metrics.md` reports DA, OU, and MSQ for every model under `results/`. See the [evaluation guide](eval/README.md) for options and output formats.

## 📁 Repository Layout

| Directory                                                      | Contents                                                         |
| -------------------------------------------------------------- | ---------------------------------------------------------------- |
| [`data/`](data/README.md)                                     | 166 task documents and task categories                           |
| [`eval/`](eval/README.md)                                     | DA / OU / MSQ evaluators and released results                    |
| [`docker/`](docker/README.md), [`enroot/`](enroot/README.md) | Docker and Enroot runtime builds                                 |
| [`toolathlon_gym/`](toolathlon_gym/run_sh_eval/README.md)     | Submodule: benchmark environment, MCP servers, and run launchers |
| `kimi-code/`                                                 | Submodule: Kimi-Code agent harness                               |
| [`visualize_script/`](visualize_script/README.md)             | Scripts for the paper figures                                    |
| `assets/`                                                    | Figures and case visualizations                                  |
| `results/`                                                   | Your runs and reports (git-ignored)                              |

## 🙏 Acknowledgements

MS-Eval builds on two open-source projects; we thank their authors for releasing them.

- **[Kimi-Code](https://github.com/MoonshotAI/kimi-code)** (Moonshot AI, MIT License) is the agent framework under our harness; both the MAD-SAE and SA paradigms run on it. We use its development version at commit [`0b2e803d`](https://github.com/MoonshotAI/kimi-code/commit/0b2e803d5e71afaab45212bb2ee6117ecbf8bbc9) (2026-08-07, after v0.34.0), plus one patch that stores oversized tool outputs inside the task workspace. The pinned source is the [`kimi-code`](kimi-code) submodule.
- **[Toolathlon-Gym](https://github.com/eigent-ai/toolathlon_gym)** (Eigent AI, Apache License 2.0), an extension of [Toolathlon](https://github.com/hkust-nlp/Toolathlon) by HKUST-NLP, provides the tasks, MCP servers, and database. We started from its development version at commit [`45bbff8`](https://github.com/eigent-ai/toolathlon_gym/commit/45bbff81419fedbb6d5a2cb46029d2980a7c93c4) (2026-07-22) and revised it for the 166 MS-Eval tasks:

  - **Task requirements:** clarified the task descriptions of 120 tasks.
  - **Checklists:** revised the evaluation checks of 150 tasks, and the initial states or reference outputs of 61.
  - **MCP servers:** fixed and hardened 14 servers.

  The revised version is the [`toolathlon_gym`](toolathlon_gym) submodule.

## 📝 Citation

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

## 📄 License

MS-Eval is released under the [MIT License](LICENSE).
