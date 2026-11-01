# Released Results

English | [简体中文](README.zh-CN.md)

[DA](../delegation_appropriateness/README.md) results for the 11 configurations reported in the paper, each covering all 166 tasks. Values are percentages with one decimal, as in the paper; each mode links to its per-task CSV. Directory names follow the paper runs: `auto-spec` and `auto-gen` are the launcher variants `spec` and `gen`.

| Model | Mode | UDR ↓ | ODR ↓ | P<sub>hit</sub> ↑ | R<sub>hit</sub> ↑ | F1<sub>hit</sub> ↑ |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Claude-Sonnet-5 | [auto-spec](claude-sonnet-5/auto-spec/task_metrics.csv) | 39.3 | 29.8 | 31.1 | 31.7 | 31.4 |
| DeepSeek-V4-Flash-0731 | [auto-spec](deepseek-v4-flash-0731/auto-spec/task_metrics.csv) | 16.8 | 57.1 | 41.0 | 56.2 | 47.4 |
| DeepSeek-V4-Flash-0731 | [auto-gen](deepseek-v4-flash-0731/auto-gen/task_metrics.csv) | 52.8 | 9.0 | 48.0 | 18.8 | 27.1 |
| DeepSeek-V4-Flash-0731 | [plan1st](deepseek-v4-flash-0731/plan1st/task_metrics.csv) | 15.7 | 61.0 | 38.4 | 51.7 | 44.1 |
| DeepSeek-V4-Flash-0731 | [oracle](deepseek-v4-flash-0731/oracle/task_metrics.csv) | 2.2 | 1.3 | 88.8 | 96.6 | 92.5 |
| GLM-5.3 | [auto-spec](glm-5.3/auto-spec/task_metrics.csv) | 8.9 | 64.9 | 46.4 | 56.9 | 51.1 |
| GLM-5.3-Flash | [auto-spec](glm-5.3-flash/auto-spec/task_metrics.csv) | 26.9 | 50.6 | 43.2 | 32.4 | 37.0 |
| GPT-5.6-Sol | [auto-spec](gpt-5.6-sol/auto-spec/task_metrics.csv) | 7.8 | 93.5 | 29.6 | 66.7 | 41.0 |
| Kimi-K3 | [auto-spec](kimi-k3/auto-spec/task_metrics.csv) | 50.5 | 16.8 | 52.7 | 25.2 | 34.1 |
| MiniMax-M3 | [auto-spec](minimax-m3/auto-spec/task_metrics.csv) | 79.7 | 9.0 | 29.4 | 10.5 | 15.5 |
| Qwen-3.8-Max | [auto-spec](qwen-3.8-max/auto-spec/task_metrics.csv) | 15.7 | 59.7 | 46.7 | 48.6 | 47.6 |

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
