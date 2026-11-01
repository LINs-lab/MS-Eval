# 已发布结果

[English](README.md) | 简体中文

论文中 11 组配置的 [DA](../delegation_appropriateness/README.zh-CN.md) 结果，每组覆盖全部 166 个任务。数值为百分比；点击模式名可查看逐任务 CSV。目录名沿用论文实验：`auto-spec`、`auto-gen` 即启动脚本中的 `spec`、`gen` 模式。

| 模型 | 模式 | UDR ↓ | ODR ↓ | P<sub>hit</sub> ↑ | R<sub>hit</sub> ↑ | F1<sub>hit</sub> ↑ |
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

OU 与 MSQ 还需要执行轨迹才能计算（见[评测指南](../README.zh-CN.md)）；论文中的 MSQ 结果见[项目主页](../../README.zh-CN.md#results)。

## 文件说明

每个 `<model>/<mode>/` 目录包含：

| 文件 | 内容 |
| --- | --- |
| `summary.json` | 汇总的 UDR、ODR、命中指标与覆盖率 |
| `task_metrics.csv` | 逐任务的委派判定与 `hit_*` 指标 |
| `task_metrics.json` | 同上，另含匹配单元与标签引用 |
| `input_summary.csv` | 作为输入的运行汇总 |
| `comparison.csv` | 与论文原始得分的逐任务核对 |

`comparison_summary.{csv,json}` 汇总上述核对结果：11 组配置均与论文结果完全一致。

| `hit_*` 字段 | 含义 |
| --- | --- |
| `hit_gt_total` / `hit_actual_total` | 金标准 / 实际单元数 |
| `hit_matched` | 匹配单元数 |
| `hit_precision` / `hit_recall` | `matched / actual_total` / `matched / gt_total` |
| `hit_f1` | `2 × matched / (gt_total + actual_total)` |
