# 编排效用（OU）

[English](README.md) | 简体中文

在主 Agent 实际发生委派的任务上，比较 MAD-SAE 与单 Agent（SA）基线。各效用取值范围为 [0, 1]：**0.5 表示持平**，越高越有利于 MAD-SAE。

| 效用 | 公式 | 任务集合 |
| --- | --- | --- |
| **U<sub>p</sub>** 性能 | `SR_mad / (SR_mad + SR_sa)` | `D_del` |
| **U<sub>e</sub>** 效率 | `Csteps_sa / (Csteps_mad + Csteps_sa)` | `D_del+` |
| **U<sub>c</sub>** 成本 | `Cost_sa / (Cost_mad + Cost_sa)` | `D_del+` |

- `D_del`：MAD-SAE 运行中至少调用了一个非规划子 Agent（依据 DA 输出），且两次运行均有汇总记录的任务。`D_del+`：其中被 MAD-SAE 成功完成的子集。
- `SR` 为成功率，`Csteps` 和 `Cost` 分别为平均关键步数和单任务平均费用。SA 在同一组任务上取值，不要求 SA 成功。

## 使用方法

先对两个实验运行[汇总脚本](../common/README.zh-CN.md)，并对 MAD-SAE 实验运行 [DA 评测](../delegation_appropriateness/README.zh-CN.md)。

```bash
python3 -m eval.orchestration_utilities.evaluate \
  --mad results/MODEL/spec --sa results/MODEL/sa \
  --out results/MODEL/spec/utilities.json
```

| 参数 | 说明 |
| --- | --- |
| `--mad DIR` | MAD-SAE 实验目录（必填） |
| `--sa DIR` | SA 基线目录（必填） |
| `--out FILE` | 输出 JSON（默认输出到 stdout） |
| `--da DIR` | DA 输出目录（默认与 `--mad` 相同） |
| `--include-failed` | 仅用于诊断：将 MAD-SAE 失败任务计入 U<sub>e</sub> / U<sub>c</sub>，与论文设定不同 |

输出包含三个效用值、对应的成功数与均值，以及缺少 DA 覆盖或配对汇总的任务。任务集合为空时结果为 `null`。

费用取自 `summary.csv` 的 `total-Cost`，按 [`pricing.json`](pricing.json) 计价，详见[费用估算](../common/README.zh-CN.md#cost-estimation)。
