# Evaluation

English | [简体中文](README.zh-CN.md)

Compute **Delegation Appropriateness (DA)** and **Orchestration Utilities (OU)** from benchmark runs, then combine them into **MSQ**. Python 3.10+, standard library only. Run every command from the repository root.

| Module | Output |
| --- | --- |
| [`common`](common/README.md) | Per-task `summary.csv`: outcome, critical steps, tokens, cost |
| [`delegation_appropriateness`](delegation_appropriateness/README.md) | UDR, ODR, P / R / F1<sub>hit</sub> |
| [`orchestration_utilities`](orchestration_utilities/README.md) | U<sub>p</sub>, U<sub>e</sub>, U<sub>c</sub> |
| `summarize.py` | Combined DA / OU / MSQ table |
| [`eval_results`](eval_results/README.md) | DA results reported in the paper |

## 1. Inputs

The scripts read the [launcher](https://github.com/Danield21/toolathlon_gym/blob/main/run_sh_eval/README.md) output as is, one directory per model and variant:

```text
results/MODEL/              # e.g. kimi-k3
├── spec/                   # MAD-SAE; likewise gen/, plan1st/, oracle/
│   └── RUN_ID/TASK_ID/RUN_ID_slotN/
│       ├── audit.html
│       └── .../raw_stream.jsonl
└── sa/                     # SA baseline
```

All runs of a variant are merged. If a task was run more than once, the latest run counts.

## 2. Compute metrics

```bash
MODEL=kimi-k3

# Per-task summaries -> summary.csv in each variant directory
python3 -m eval.common.build_audit_summary results/$MODEL/spec results/$MODEL/sa

# DA -> summary.json, task_metrics.{json,csv}
export DELEGATE_LLM_API_KEY=...   # LLM reviewer for sub-agent labels
python3 -m eval.delegation_appropriateness.evaluate \
  --dump results/$MODEL/spec --out results/$MODEL/spec --match

# DA + OU + MSQ for every model and variant under results/
python3 -m eval.summarize --root results > results/metrics.md
```

- Other variants: replace `spec` with `gen`, `plan1st` or `oracle`. Each is compared with the same `sa/` baseline.
- `--match` calls the API only for sub-agents missing from the [label cache](delegation_appropriateness/delegate_llm_tag_cache/README.md); all runs reported in the paper are cached. See [LLM reviewer](delegation_appropriateness/README.md#llm-reviewer).
- Costs use the price listed for `MODEL` in [`eval/orchestration_utilities/pricing.json`](orchestration_utilities/pricing.json). For a new model, add its price there before running `build_audit_summary`, or all costs are 0. See [cost estimation](common/README.md#cost-estimation).
- OU for one pair as JSON: `python3 -m eval.orchestration_utilities.evaluate --mad results/$MODEL/spec --sa results/$MODEL/sa`.

## 3. Read the results

Example row of `results/metrics.md`:

| experiment | P_hit | R_hit | F1_hit | UDR | ODR | U_p | U_e | U_c | MSQ |
|---|---|---|---|---|---|---|---|---|---|
| kimi-k3/spec | 52.76% | 25.28% | 34.18% | 50.56% (45/89) | 16.88% (13/77) | 0.5647 (48/37) | 0.5038 (43.56/44.23) | 0.5096 ($4.4905/$4.6669) | 0.1798 |

- UDR and ODR: lower is better; parentheses give the task counts.
- Hit scores and utilities: higher is better. A utility of **0.5 means parity** with SA; parentheses give MAD-SAE / SA successes, mean critical steps, and mean cost per task.
- `MSQ = F1_hit × (U_p + U_e + U_c) / 3`.
- Tasks without traces are excluded and reported as missing coverage. Undefined values appear as `-` (`null` in JSON, empty in CSV).

Metric definitions: [main README](../README.md#metrics) and the paper.
