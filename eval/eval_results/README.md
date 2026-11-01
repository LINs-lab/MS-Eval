# Released Results

English | [简体中文](README.zh-CN.md)

[DA](../delegation_appropriateness/README.md) results for the 11 configurations reported in the paper, each covering all 166 tasks. Values are percentages; each mode links to its per-task CSV. Directory names follow the paper runs: `auto-spec` and `auto-gen` are the launcher variants `spec` and `gen`.

| Model | Mode | UDR ↓ | ODR ↓ | P<sub>hit</sub> ↑ | R<sub>hit</sub> ↑ | F1<sub>hit</sub> ↑ |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Claude-Sonnet-5 | [auto-spec](claude-sonnet-5/auto-spec/task_metrics.csv) | 39.33 | 29.87 | 31.11 | 31.70 | 31.40 |
| DeepSeek-V4-Flash-0731 | [auto-spec](deepseek-v4-flash-0731/auto-spec/task_metrics.csv) | 16.85 | 57.14 | 41.05 | 56.23 | 47.45 |
| DeepSeek-V4-Flash-0731 | [auto-gen](deepseek-v4-flash-0731/auto-gen/task_metrics.csv) | 52.81 | 9.09 | 48.08 | 18.87 | 27.10 |
| DeepSeek-V4-Flash-0731 | [plan1st](deepseek-v4-flash-0731/plan1st/task_metrics.csv) | 15.73 | 61.04 | 38.48 | 51.70 | 44.12 |
| DeepSeek-V4-Flash-0731 | [oracle](deepseek-v4-flash-0731/oracle/task_metrics.csv) | 2.25 | 1.30 | 88.89 | 96.60 | 92.59 |
| GLM-5.3 | [auto-spec](glm-5.3/auto-spec/task_metrics.csv) | 8.99 | 64.94 | 46.46 | 56.98 | 51.19 |
| GLM-5.3-Flash | [auto-spec](glm-5.3-flash/auto-spec/task_metrics.csv) | 26.97 | 50.65 | 43.22 | 32.45 | 37.07 |
| GPT-5.6-Sol | [auto-spec](gpt-5.6-sol/auto-spec/task_metrics.csv) | 7.87 | 93.51 | 29.65 | 66.79 | 41.07 |
| Kimi-K3 | [auto-spec](kimi-k3/auto-spec/task_metrics.csv) | 50.56 | 16.88 | 52.76 | 25.28 | 34.18 |
| MiniMax-M3 | [auto-spec](minimax-m3/auto-spec/task_metrics.csv) | 79.78 | 9.09 | 29.47 | 10.57 | 15.56 |
| Qwen-3.8-Max | [auto-spec](qwen-3.8-max/auto-spec/task_metrics.csv) | 15.73 | 59.74 | 46.74 | 48.68 | 47.69 |

OU and MSQ also need the execution traces ([evaluation guide](../README.md)); the paper's MSQ values are shown in the [main README](../../README.md#results).

## Files

Each `<model>/<mode>/` contains:

| File | Contents |
| --- | --- |
| `summary.json` | Aggregate UDR, ODR, hit scores, and coverage |
| `task_metrics.csv` | Per-task delegation decision and `hit_*` scores |
| `task_metrics.json` | Same, plus matched units and label references |
| `input_summary.csv` | Run summary used as input |
| `comparison.csv` | Per-task check against the original paper scores |

`comparison_summary.{csv,json}` aggregates these checks: all 11 configurations reproduce the paper exactly.

| `hit_*` column | Meaning |
| --- | --- |
| `hit_gt_total` / `hit_actual_total` | Golden / executed units |
| `hit_matched` | Matched units |
| `hit_precision` / `hit_recall` | `matched / actual_total` / `matched / gt_total` |
| `hit_f1` | `2 × matched / (gt_total + actual_total)` |
