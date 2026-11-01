# 运行汇总

[English](README.md) | 简体中文

生成 DA 与 OU 评测器读取的逐任务 `summary.csv`。任务结果和关键步数取自每次运行的 `audit.html`；token 用量取自主 Agent 及全部子 Agent 的 Kimi 会话日志（`wire.jsonl`）。

## 使用方法

```bash
python3 -m eval.common.build_audit_summary results/MODEL/spec results/MODEL/sa
```

在每个模式目录下写入 `summary.csv`。也可传入模型目录或 `results/` 本身，模式目录会被自动发现。同一模式下的各次 `RUN_ID/` 运行会合并；同一任务有多次运行时，使用最近一次。使用 `-o PATH` 可写到其他位置（仅限单个模式）。

## 字段

| 字段 | 含义 |
| --- | --- |
| `Task`、`Result` | 任务 ID；`1` 为通过，`0` 为失败 |
| `Comment` | 终止原因，如 `claim_done`、`timeout`、`100_step_limit`、`API Error` |
| `Critical Steps` | 主 Agent 步数，每次委派再加上其中最慢子 Agent 的步数；不含 API 报错步 |
| `Subagent-Delegate` | 有任一子 Agent 运行即为 `1`，包括仅做规划的子 Agent |
| `Duration`、`Checkpoints`、`API Error Steps(main-agent/subagent)` | 取自审计页面 |
| `inputOther`、`inputCacheRead`、`inputCacheCreation`、`output` | token 用量 |
| `Input-Cost`、`inputCacheRead-Cost`、`output-Cost`、`total-Cost` | 估算费用（美元） |
| `audit.html` | 所选审计页面，路径相对于 CSV |

<a id="cost-estimation"></a>

## 费用估算

`build_audit_summary` 按 [`eval/orchestration_utilities/pricing.json`](../orchestration_utilities/pricing.json) 中的价格计算 token 费用，单位为美元 / 百万 token。价格按模型目录名（`results/MODEL/` 中的 `MODEL`）查找。缓存写入 token 不计费。

该文件中没有的模型，费用记为 0。添加方法：

1. 在 `eval/orchestration_utilities/pricing.json` 的 `"models"` 下添加一项。键名须与模型目录名完全一致，三个数依次为非缓存输入、缓存输入和输出的单价：

   ```json
   "my-model": [1.00, 0.10, 4.00]
   ```

2. 运行 `build_audit_summary`；若已生成过 `summary.csv`，需重新运行。输出中应显示 `model=my-model`；若显示 `model=None` 和 `[warn] no pricing key`，说明键名与目录名不一致。

分档计价的模型写在 `"tiered_models"` 下，格式参照 `minimax-m3`。单次请求的输入 token 数超过 `input_token_threshold` 时按 `above` 档计费；`minimax-m3` 的阈值为 512K，`gpt-5.6-sol` 为 272K。
