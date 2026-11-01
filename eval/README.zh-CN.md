# 评测

[English](README.md) | 简体中文

基于 benchmark 运行结果计算**委派适当性（DA）**与**编排效用（OU）**，并合成 **MSQ**。需要 Python 3.10+，仅依赖标准库。所有命令均在仓库根目录执行。

| 模块 | 输出 |
| --- | --- |
| [`common`](common/README.zh-CN.md) | 逐任务 `summary.csv`：任务结果、关键步数、token 与费用 |
| [`delegation_appropriateness`](delegation_appropriateness/README.zh-CN.md) | UDR、ODR、P / R / F1<sub>hit</sub> |
| [`orchestration_utilities`](orchestration_utilities/README.zh-CN.md) | U<sub>p</sub>、U<sub>e</sub>、U<sub>c</sub> |
| `summarize.py` | DA / OU / MSQ 汇总表 |
| [`eval_results`](eval_results/README.zh-CN.md) | 论文报告的 DA 结果 |

## 1. 输入

脚本直接读取[启动脚本](https://github.com/Danield21/toolathlon_gym/blob/main/run_sh_eval/README.zh-CN.md)的输出，每个模型的每种模式对应一个目录：

```text
results/MODEL/              # 如 kimi-k3
├── spec/                   # MAD-SAE；gen/、plan1st/、oracle/ 同理
│   └── RUN_ID/TASK_ID/RUN_ID_slotN/
│       ├── audit.html
│       └── .../raw_stream.jsonl
└── sa/                     # SA 基线
```

同一模式下的多次运行会合并；同一任务运行过多次时，以最近一次为准。

## 2. 计算指标

```bash
MODEL=kimi-k3

# 逐任务汇总 -> 各模式目录下的 summary.csv
python3 -m eval.common.build_audit_summary results/$MODEL/spec results/$MODEL/sa

# DA -> summary.json、task_metrics.{json,csv}
export DELEGATE_LLM_API_KEY=...   # 子 Agent 功能标签的 LLM 审核模型
python3 -m eval.delegation_appropriateness.evaluate \
  --dump results/$MODEL/spec --out results/$MODEL/spec --match

# 汇总 results/ 下所有模型和模式的 DA + OU + MSQ
python3 -m eval.summarize --root results > results/metrics.md
```

- 其他模式：将 `spec` 换成 `gen`、`plan1st` 或 `oracle`，均与同一个 `sa/` 基线对比。
- `--match` 只为[标签缓存](delegation_appropriateness/delegate_llm_tag_cache/README.zh-CN.md)中缺失的子 Agent 调用 API；论文中的全部运行均已缓存。详见 [LLM 审核模型](delegation_appropriateness/README.zh-CN.md#llm-reviewer)。
- 费用按 [`eval/orchestration_utilities/pricing.json`](orchestration_utilities/pricing.json) 中 `MODEL` 的价格计算。评测新模型时，需在运行 `build_audit_summary` 前把价格加入该文件，否则费用均为 0。详见[费用估算](common/README.zh-CN.md#cost-estimation)。
- 单独输出一组对比的 OU（JSON）：`python3 -m eval.orchestration_utilities.evaluate --mad results/$MODEL/spec --sa results/$MODEL/sa`。

## 3. 解读结果

`results/metrics.md` 示例：

| experiment | P_hit | R_hit | F1_hit | UDR | ODR | U_p | U_e | U_c | MSQ |
|---|---|---|---|---|---|---|---|---|---|
| kimi-k3/spec | 52.7% | 25.2% | 34.1% | 50.5% (45/89) | 16.8% (13/77) | 56.4% (48/37) | 50.3% (43.56/44.23) | 50.9% ($4.4905/$4.6669) | 17.9% |

- 所有指标均为保留一位小数的百分比，与论文数值一致。
- UDR、ODR 越低越好，括号内为任务计数。
- 命中指标与效用越高越好。效用 **50% 表示与 SA 持平**；括号内依次为 MAD-SAE / SA 的成功数、平均关键步数和单任务平均费用。
- `MSQ = F1_hit × (U_p + U_e + U_c) / 3`。
- 缺少执行轨迹的任务不参与计分，并计入覆盖率缺失。未定义值显示为 `-`（JSON 中为 `null`，CSV 中为空）。

指标定义见[项目主页](../README.zh-CN.md#metrics)和论文。
